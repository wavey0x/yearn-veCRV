import math, time
from brownie import Contract
import time


def test_operations(Strategy, accounts, live_strat, voter, token, new_proxy, trade_factory, ymechs_safe, ybal, whale_ybal, eth_whale, st_ybal, st_strategy, strategist, amount, user, bbausd, bal, chain, whale_bbausd, whale_bal, gov):
    assert st_ybal.withdrawalQueue(0) == st_strategy.address
    gasOracle = Contract("0xb5e1CAcB567d98faaDB60a1fD4820720141f064F")
    gasOracle.setMaxAcceptableBaseFee(2000 * 1e9, {"from": st_ybal.management()})
    bbausd.transfer(st_strategy, 10e20, {"from": whale_bbausd})
    bal.transfer(st_strategy, 10e20, {"from": whale_bal})
    # assert not strategy.harvestTrigger(1e9)
    ybal.transfer(st_strategy, 1e18, {"from": whale_ybal})
    assert st_strategy.harvestTrigger(1e9)

    vault_before = ybal.balanceOf(st_ybal)
    strat_before = ybal.balanceOf(st_strategy)
    # Deposit to the vault
    ybal.approve(st_ybal.address, amount, {"from": user})
    st_ybal.deposit(amount, {"from": user})
    assert ybal.balanceOf(st_ybal.address) == amount + vault_before
    st_strategy.harvest({'from': strategist})

def test_ybal_functionality(Strategy, balweth, whale_crv, accounts, live_strat, voter, token, new_proxy, trade_factory, ymechs_safe, ybal, whale_ybal, eth_whale, st_ybal, st_strategy, strategist, amount, user, crv3, chain, whale_3crv, gov):
    # Test transfer
    balweth.approve(ybal, 100e18, {'from':user})
    ybal.mint(100e18, {'from':user})

    # Test Deposit
    before = ybal.balanceOf(user)
    ybal.deposit(100e18, {'from':user})
    assert ybal.balanceOf(user) > before

    # Test Claim
    ybal.claim({"from":user})

    # Test Update
    ybal.claim({"from":user})

    # Test Lock
    ybal.transfer(strategist, 200e18, {"from":whale_ybal})

    # Pass 1 week for next reward period
    chain.sleep(60 * 60 * 24 * 7)
    chain.mine()

    ybal.transfer(strategist, 200e18, {"from":whale_ybal})

    # test claim
    bal = crv3.balanceOf(whale_ybal)
    ybal.claim({"from":whale_ybal})
    assert bal < crv3.balanceOf(whale_ybal)

    # Test claim for
    pool = "0x10B47177E92Ef9D5C6059055d92DdF6290848991"
    pool = "0x1b9524b0F0b9F2e16b5F9e4baD331e01c2267981"
    bal = crv3.balanceOf(pool)
    ybal.claimFor(pool, {"from":whale_ybal})
    assert bal < crv3.balanceOf(pool)

    chain.sleep(60 * 60 * 24 * 7)
    chain.mine()
    ybal.transfer(strategist, ybal.balanceOf(whale_ybal), {"from":whale_ybal})
    ybal.claim({"from":whale_ybal})

    ybal.transfer(whale_ybal, 200e18, {"from":strategist})

def test_change_debt(gov, Strategy, live_strat, token, new_proxy, voter, trade_factory, st_ybal, ymechs_safe, st_strategy, strategist, amount, user):
    if st_ybal.withdrawalQueue(0) != st_strategy.address:
        st_ybal.migrateStrategy(live_strat, st_strategy, {"from": gov})
    # Deposit to the vault and harvest
    before = st_strategy.estimatedTotalAssets()
    st_ybal.updateStrategyDebtRatio(st_strategy.address, 5_000, {"from": gov})
    st_strategy.harvest({"from":strategist})
    after = st_strategy.estimatedTotalAssets()
    assert after > before
    st_ybal.updateStrategyDebtRatio(st_strategy.address, 10_000, {"from": gov})
    st_strategy.harvest({"from":strategist})
    assert after < st_strategy.estimatedTotalAssets()

def test_migrate(Strategy, accounts, live_strat, token, new_proxy, voter, ybal, whale_bbausd, whale_bal, eth_whale, st_ybal, st_strategy, strategist, amount, user, bbausd, bal, chain, gov):
    #balweth.approve(ybal, 100e18, {'from':user})
    ybal.mint(100e18, {'from':user})
    new_proxy.lock()
    ybal.transfer(st_strategy, 100e18, {"from": user})
    bbausd.transfer(st_strategy, 100e18, {"from": whale_bbausd})
    bal.transfer(st_strategy, 100e18, {"from": whale_bal})
    old_bal1 = ybal.balanceOf(st_strategy)
    old_bal2 = bbausd.balanceOf(st_strategy)
    old_bal3 = bal.balanceOf(st_strategy)
    st_strategy.harvest({'from': strategist}) # failing because of _claim (nothing to claim?)
    new = strategist.deploy(Strategy, st_ybal)
    st_ybal.migrateStrategy(st_strategy, new, {'from':gov})
    new_bal1 = token.balanceOf(new)
    new_bal2 = bbausd.balanceOf(new)
    new_bal3 = bal.balanceOf(new)
    assert old_bal1 == new_bal1
    assert old_bal2 == new_bal2
    assert old_bal3 == new_bal3