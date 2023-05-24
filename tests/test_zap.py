import math, time, brownie, requests
from re import A
from brownie import Contract, accounts, web3
import time
from eth_abi import encode
from brownie.convert import to_bytes

def test_zap(zap, strategist, input_tokens, output_tokens, 
             amount, user, chain, weth, ybal, st_ybal, 
             lp_ybal, gov, bal, balweth, pool, balancer_vault,
             using_tenderly
    ):
    
    recipient = user

    # To make testing easy, we loosen up our buffer
    zap.set_mint_buffer(499, {'from':gov})
    supply_a_lot_of_liquidity(user, ybal, pool)
    
    for i in input_tokens:
        input_token = Contract(i)
        grant_allowance(user, zap, i)
        for o in output_tokens:
            output_token = Contract(o)
            user_input_token_balance_before = input_token.balanceOf(user)
            recipient_output_token_balance_before = output_token.balanceOf(recipient)
            _amount = 100e18
            print(f'{_amount/1e18:,} {input_token.symbol()} --> {output_token.symbol()}')
            print_state_of_pool(pool, pool.getPoolId(), balancer_vault)
            if i.lower() == o.lower():
                if not using_tenderly:
                    with brownie.reverts():
                        tx = zap.zap(i, o, _amount, 0)
                print(f'Same token. Skipping... ')
                continue
            if using_tenderly:
                expected_mint_out = zap.zap.call(
                    i,          # input token 
                    o,          # output token
                    _amount,      # amount
                    0,          # min out
                    recipient,  # recipient (optional)
                    True,       # mint (optional)
                    {'from': user}
                )
                expected_swap_out = zap.zap.call(
                    i,          # input token 
                    o,          # output token
                    _amount,      # amount
                    0,          # min out
                    recipient,  # recipient (optional)
                    False,      # mint (optional)
                    {'from': user}
                )
                _min_out, _mint = compute_inputs(zap, expected_mint_out, expected_swap_out)
            else:
                _min_out, _mint = compute_inputs(zap, 0, 0)
            
            tx = zap.zap(
                i,          # input token 
                o,          # output token
                _amount,    # amount
                _min_out,   # min out
                recipient,  # recipient (optional)
                _mint,      # mint (optional)
            )

            user_input_token_balance_after = input_token.balanceOf(user)
            recipient_output_token_balance_after = output_token.balanceOf(recipient)
            net_output = recipient_output_token_balance_after - recipient_output_token_balance_before
            if using_tenderly:
                if i in output_tokens:
                    print(f'Mint/Swap in doesn\'t make a difference')
                else:
                    print(f'Output on MINT: {expected_mint_out/1e18}')
                    print(f'Output on SWAP: {expected_swap_out/1e18}')

            minted = 'Mint' in tx.events
            string = "Minted" if minted else "Swapped"
            if i not in output_tokens:
                assert minted == _mint
            else:
                assert minted == False
                string = "N/A"
            print(f'Actual: {string} {net_output/1e18}')
            print(f'Gas Used: {tx.gas_used:,}')
            print()
            # Checks
            assert user_input_token_balance_before > user_input_token_balance_after
            assert recipient_output_token_balance_before < recipient_output_token_balance_after
            # Ensure there's never any dust left in the contract
            verify_zero_balances(zap, input_tokens, output_tokens)

def test_sweep(weth, usdt, zap, user, gov, using_tenderly):
    weth.transfer(zap, 1e18, {'from':user})
    before = weth.balanceOf(gov)
    zap.sweep(weth, {'from':gov})
    assert weth.balanceOf(gov) > before

    if not using_tenderly:
        with brownie.reverts():
            zap.sweep(weth, {'from':user})

    before = usdt.balanceOf(gov)
    usdt.transfer(zap, 10e6, {'from':user})
    zap.sweep(usdt, {'from':gov})
    assert usdt.balanceOf(gov) > before

    if not using_tenderly:
        with brownie.reverts():
            zap.sweep(usdt, {'from':user})

def test_change_buffer(zap, user, gov, using_tenderly):
    new_buffer = 99
    assert zap.mint_buffer() != new_buffer
    zap.set_mint_buffer(new_buffer, {'from':gov})
    assert zap.mint_buffer() == 99

    if not using_tenderly:
        with brownie.reverts():
            zap.set_mint_buffer(new_buffer, {'from':user})

def verify_zero_balances(zap, input_tokens, output_tokens):
    for t in input_tokens:
        assert Contract(t).balanceOf(zap) == 0
    for t in output_tokens:
        assert Contract(t).balanceOf(zap) == 0

def grant_allowance(user, zap, i):
    token = Contract(i)
    token.approve(zap, 2**256-1, {'from': user})

def supply_a_lot_of_liquidity(user, ybal, pool):

    voter = Contract('0xBA11E7024cbEB1dd2B401C70A83E0d964144686C')
    ybal = Contract('0x98E86Ed5b0E48734430BfBe92101156C75418cad', owner=user)
    token = Contract(voter.token(), owner=user)
    gov = voter.governance()
    INITIAL_BPT_SUPPLY = 2 ** (112) - 1

    half = int(token.balanceOf(user) / 2)
    to_mint = half
    half = half - 10 ** 16
    token.approve(ybal, 2**256-1)
    tx = ybal.mint(to_mint)

    pool = Contract('0xD61e198e139369a40818FE05F5d5e6e045Cd6eaF', owner=user)
    pool_id = to_bytes(pool.getPoolId(), "bytes32")
    vault = Contract(pool.getVault(),owner=user)
    tokens = list(vault.getPoolTokens(pool_id)[0])

    pool = Contract('0xD61e198e139369a40818FE05F5d5e6e045Cd6eaF', owner=user)
    vault = Contract(pool.getVault(),owner=user)
    tokens = list(vault.getPoolTokens(pool_id)[0])

    INITIAL_BPT_SUPPLY = 2 ** (112) - 1
    
    half = 1_000 * 10 ** 18
    
    # Token approvals to vault
    for t in tokens:
        t = Contract(t,owner=user)
        t.allowance(user, vault)
        t.approve(vault, 2**256-1)

    user_data = encode(
        ["uint256", "uint256[]", "uint256"], # ABI
        (
            1, # JoinKind
            [
                half,
                half
            ],
            0
        ),  # Amounts in
    )

    request = (
        tokens,                             # assets[]
        [half, half, INITIAL_BPT_SUPPLY],   # maxAmountsIn[]
        user_data,                          # userData
        False                               # fromInternalBalance
    )

    tx = vault.joinPool(
        pool_id,    # poolID
        user,      # sender
        user,      # recipient
        request,    # request
    )

    print_state_of_pool(pool, pool_id, vault)

def print_state_of_pool(pool, pool_id, vault):
    print(f'--- Pool Balances ---')
    for i in range(0,2):
        balance = vault.getPoolTokens(pool_id)['balances'][i]
        token = Contract(vault.getPoolTokens(pool_id)['tokens'][i])
        print(f'{token.symbol()} {balance/1e18}')
    print('---')

def compute_inputs(zap, expected_mint_out, expected_swap_out):
    buffer = zap.mint_buffer()
    slippage_tolerance = 0.01 # (1%)
    buffered_amount = (
        expected_swap_out - 
        (expected_swap_out * buffer / 10_000)
    )

    if buffered_amount > expected_mint_out:
        _mint = False
        _min_out = buffered_amount * (1 - slippage_tolerance)
    else:
        _mint = True
        _min_out = expected_mint_out * (1 - slippage_tolerance)

    return _min_out, _mint