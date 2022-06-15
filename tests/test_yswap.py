import brownie
import pytest
import eth_utils

from eth_abi.packed import encode_abi_packed

def test_yswap(
    gov,
    vault,
    strategy,
    strategist,
    token,
    amount,
    RELATIVE_APPROX,
    yveCrv,
    weth,
    usdc,
    crv3,
    crv,
    chain,
    whale_3crv,
    user,
    trade_factory,
    sushiswap,
    ymechs_safe,
    multicall_swapper,
    curvefi_3crv_pool,
    Strategy,
    new_proxy,
    voter,
    live_strat,
    keeper
):
    vault_before = token.balanceOf(vault)
    strat_before = token.balanceOf(strategy)

    # harvest
    chain.sleep(1)
    chain.mine(1)
    strategy.harvest({"from": strategist})
    # assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == (strat_before + vault_before)

    # Simulate a claim by sending some 3Crv to the strategy before harvest
    crv3.transfer(strategy, brownie.Wei("100 ether"), {"from": whale_3crv})
    strategy.harvest({"from": strategist})
    chain.sleep(60*60*6) # sleep to increase pps
    chain.mine(1)

    # Execute ySwap trades
    print(f"Executing trades...")

    token_in = crv3
    token_out = yveCrv

    print(f"Executing trade...")
    receiver = strategy.address
    amount_in = token_in.balanceOf(strategy)

    asyncTradeExecutionDetails = [strategy, token_in, token_out, amount_in, 1]

    # always start with optimizations. 5 is CallOnlyNoValue
    optimizations = [["uint8"], [5]]
    a = optimizations[0]
    b = optimizations[1]

    crv3_amt = brownie.Wei("1 ether")


    # Expected USDC when lp tokens are exchanged....
    expected_usdc = curvefi_3crv_pool.calc_withdraw_one_coin(crv3_amt, 1)

    ## Remove amount of liquidity all in a form of coin USDC and a min of expected_usdc
    calldata = curvefi_3crv_pool.remove_liquidity_one_coin.encode_input(crv3_amt, 1, expected_usdc)
    t = create_tx(curvefi_3crv_pool, calldata)
    a  = a + t[0]
    b = b + t[1]

    calldata = usdc.approve.encode_input(sushiswap, expected_usdc)
    t = create_tx(usdc, calldata)
    a = a + t[0]
    b = b + t[1]

    path = [usdc.address, weth.address, crv.address]
    calldata = sushiswap.swapExactTokensForTokens.encode_input(
        expected_usdc, 0, path, multicall_swapper, 2 ** 256 - 1
    )
    t = create_tx(sushiswap, calldata)
    a = a + t[0]
    b = b + t[1]

    expected_crv = sushiswap.getAmountsOut(expected_usdc, path)[2]

    # Convert crv to yveCrv 1:1
    calldata = crv.approve.encode_input(token_out, expected_crv)
    t = create_tx(crv, calldata)
    a = a + t[0]
    b = b + t[1]

    calldata = token_out.deposit.encode_input(expected_crv)
    t = create_tx(token_out, calldata)
    a = a + t[0]
    b = b + t[1]


    # Pass the newly minted yveCrv back to the strategy
    calldata = token_out.approve.encode_input(receiver, expected_crv)
    t = create_tx(token_out, calldata)
    a = a + t[0]
    b = b + t[1]

    calldata = token_out.transfer.encode_input(receiver, expected_crv)
    t = create_tx(token_out, calldata)
    a = a + t[0]
    b = b + t[1]

    transaction = encode_abi_packed(a, b)

    trade_factory.execute['tuple,address,bytes'](
        asyncTradeExecutionDetails, multicall_swapper.address, transaction, {"from": ymechs_safe}
    )
    print(token_out.balanceOf(strategy))

    tx = strategy.harvest({"from": strategist})
    print(tx.events)
    assert tx.events["Harvested"]["profit"] > 0

    vault.updateStrategyDebtRatio(strategy, 0, {'from': gov})
    strategy.harvest({'from': strategist})

    strategy.tend()

    strategy.harvest({'from': strategist})

    assert token.balanceOf(vault) > amount
    assert strategy.estimatedTotalAssets() == 0

    # Test remove trade factory
    assert strategy.tradeFactory() == trade_factory.address
    assert crv3.allowance(strategy.address, trade_factory.address) > 0

    strategy.removeTradeFactoryPermissions({'from': gov})

    assert strategy.tradeFactory() != trade_factory.address
    assert crv3.allowance(strategy.address, trade_factory.address) == 0

    # test_harvest_reverts_without_trade_factory
    vault_before = token.balanceOf(vault)
    strategy = strategist.deploy(Strategy, vault)
    strategy.setKeeper(keeper, {"from": gov})
    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 1_000, {"from": gov})

    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    assert token.balanceOf(vault.address) == vault_before + amount

    # harvest
    chain.sleep(1)

    strategy.removeTradeFactoryPermissions({'from':gov})
    with brownie.reverts("!tf"):
        strategy.harvest()


def create_tx(to, data):
    inBytes = eth_utils.to_bytes(hexstr=data)
    return [["address", "uint256", "bytes"], [to.address, len(inBytes), inBytes]]