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

    assert strategy.shouldClaim()
    strategy.toggleShouldClaim({"from": vault.management()})
    assert not strategy.shouldClaim()

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
    assert after < before
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
    assert new_bal1 > 0
    assert old_bal1 == new_bal1
    assert old_bal2 == new_bal2