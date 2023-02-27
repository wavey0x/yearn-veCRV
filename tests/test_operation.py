import math, time
from brownie import Contract
import time


def test_operations(Strategy, accounts, live_strat, voter, token, new_proxy, trade_factory, ymechs_safe, yveCrv, whale_yvecrv, eth_whale, vault, strategy, strategist, amount, user, crv3, chain, whale_3crv, gov):
    assert vault.withdrawalQueue(0) == strategy.address
    gasOracle = Contract("0xb5e1CAcB567d98faaDB60a1fD4820720141f064F")
    gasOracle.setMaxAcceptableBaseFee(2000 * 1e9, {"from": vault.management()})
    crv3.transfer(strategy, 10e20, {"from": whale_3crv})
    # assert not strategy.harvestTrigger(1e9)
    yveCrv.transfer(strategy, 1e18, {"from": whale_yvecrv})
    assert strategy.harvestTrigger(1e9)

    vault_before = token.balanceOf(vault)
    strat_before = token.balanceOf(strategy)
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    assert token.balanceOf(vault.address) == amount + vault_before
    strategy.harvest({'from': strategist})

def test_yvecrv_functionality(Strategy, crv, whale_crv, accounts, live_strat, voter, token, new_proxy, trade_factory, ymechs_safe, yveCrv, whale_yvecrv, eth_whale, vault, strategy, strategist, amount, user, crv3, chain, whale_3crv, gov):
    # Test transfer
    crv.transfer(user, 1_000e18, {'from':whale_crv})
    crv.approve(yveCrv, 1_000e18, {'from':user})

    # Test Deposit
    before = yveCrv.balanceOf(user)
    yveCrv.deposit(1_000e18, {'from':user})
    assert yveCrv.balanceOf(user) > before

    # Test Claim
    yveCrv.claim({"from":user})

    # Test Update
    yveCrv.claim({"from":user})

    # Test Lock
    yveCrv.transfer(strategist, 200e18, {"from":whale_yvecrv})

    # Pass 1 week for next reward period
    chain.sleep(60 * 60 * 24 * 7)
    chain.mine()

    yveCrv.transfer(strategist, 200e18, {"from":whale_yvecrv})

    # test claim
    bal = crv3.balanceOf(whale_yvecrv)
    yveCrv.claim({"from":whale_yvecrv})
    assert bal < crv3.balanceOf(whale_yvecrv)

    # Test claim for
    pool = "0x10B47177E92Ef9D5C6059055d92DdF6290848991"
    pool = "0x1b9524b0F0b9F2e16b5F9e4baD331e01c2267981"
    bal = crv3.balanceOf(pool)
    yveCrv.claimFor(pool, {"from":whale_yvecrv})
    assert bal < crv3.balanceOf(pool)

    chain.sleep(60 * 60 * 24 * 7)
    chain.mine()
    yveCrv.transfer(strategist, yveCrv.balanceOf(whale_yvecrv), {"from":whale_yvecrv})
    yveCrv.claim({"from":whale_yvecrv})

    yveCrv.transfer(whale_yvecrv, 200e18, {"from":strategist})

def test_change_debt(gov, Strategy, live_strat, token, new_proxy, voter, trade_factory, vault, ymechs_safe, strategy, strategist, amount, user):
    if vault.withdrawalQueue(0) != strategy.address:
        vault.migrateStrategy(live_strat, strategy, {"from": gov})
    # Deposit to the vault and harvest
    before = strategy.estimatedTotalAssets()
    vault.updateStrategyDebtRatio(strategy.address, 5_000, {"from": gov})
    strategy.harvest({"from":strategist})
    after = strategy.estimatedTotalAssets()
    assert after > before
    vault.updateStrategyDebtRatio(strategy.address, 10_000, {"from": gov})
    strategy.harvest({"from":strategist})
    assert after < strategy.estimatedTotalAssets()

def test_migrate(Strategy, accounts, live_strat, token, voter, yveCrv, whale_yvecrv, eth_whale, vault, strategy, strategist, amount, user, crv3, chain, whale_3crv, gov):
    old_bal1 = token.balanceOf(strategy)
    old_bal2 = crv3.balanceOf(strategy)
    new = strategist.deploy(Strategy, vault)
    vault.migrateStrategy(strategy, new, {'from':gov})
    new_bal1 = token.balanceOf(new)
    new_bal2 = crv3.balanceOf(new)
    # assert new_bal1 > 0
    assert old_bal1 == new_bal1
    assert old_bal2 == new_bal2

def test_remove_tf(Strategy, accounts, live_strat, token, voter, yveCrv, whale_yvecrv, eth_whale, vault, strategy, strategist, amount, user, crv3, chain, whale_3crv, gov):
    active_strat = Contract('0xAf73A48E1d7e8300C91fFB74b8f5e721fBFC5873',owner=gov)
    strategist.deploy(Strategy, vault)
    vault = Contract(active_strat.vault(),owner=gov)
    strategy = strategist.deploy(Strategy, vault)
    vault.migrateStrategy(active_strat, strategy)

    old_tf = active_strat.tradeFactory()
    new_tf = '0xb634316E06cC0B358437CbadD4dC94F1D3a92B3b'

    strategy = Strategy.at(strategy.address)
    strategy.removeTradeFactoryPermissions(True, {'from':gov})
    strategy.setTradeFactory(new_tf, {'from':gov})
    tokens = ["0x6B175474E89094C44Da98b954EedeAC495271d0F", "0x090185f2135308BaD17527004364eBcC2D37e5F6", "0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490", "0x41D5D79431A913C4aE7d69a668ecdfE5fF9DFB68", "0x865377367054516e17014CcdED1e7d814EDC9ce4", "0xE57180685E3348589E9521aa53Af0BCD497E884d", "0xD533a949740bb3306d119CC777fa900bA034cd52", "0xd395DEC4F1733ff09b750D869eEfa7E0D37C3eE6", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32"]
    for t in tokens:
        strategy.approveTokenForTradeFactory(t, {'from':gov})
    
    strategy.removeTradeFactoryPermissions(True, {'from':gov})
    