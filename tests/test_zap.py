import math, time
from brownie import Contract
import time

def test_zap(zap, pool, Strategy, accounts, voter, yvLP, whale_crv, token, yveCrv, yvboost, crv, whale_yvecrv, vault, strategy, strategist, amount, user, crv3, chain, whale_3crv, gov):
    crv.approve(zap, 2**256-1, {"from": user})
    crv.approve(pool, 2**256-1, {"from": whale_crv})
    yvboost.approve(zap, 2**256-1, {"from": user})
    yveCrv.approve(zap, 2**256-1, {"from": user})
    yvLP.approve(zap, 2**256-1, {"from": user})
    
    chain.snapshot()
    crv_before = crv.balanceOf(user)
    yv_before = yvLP.balanceOf(user)
    print("ZAP CRV --> LP VAULT\n")
    print_balances(user, yvLP, crv, yvboost, yveCrv, pool)
    zap.zapCRVtoLPVault(2e18, 0, user, {"from":user})
    print_balances(user, yvLP, crv, yvboost, yveCrv, pool)
    crv_after = crv.balanceOf(user)
    yv_after = yvLP.balanceOf(user)
    assert yv_after > yv_before
    assert crv_before > crv_after

    crv_before = crv.balanceOf(user)
    yvboost_before = yvboost.balanceOf(user)
    print("ZAP CRV --> YVBOOST\n")
    print_balances(user, yvLP, crv, yvboost, yveCrv, pool)
    zap.zapCRVtoYvBOOST(2e18, 0, user, {"from":user})
    print_balances(user, yvLP, crv, yvboost, yveCrv, pool)
    crv_after = crv.balanceOf(user)
    yvboost_after = yvboost.balanceOf(user)
    assert yvboost_after > yvboost_before
    assert crv_before > crv_after

    yvLP_before = yvLP.balanceOf(user)
    yvboost_before = yvboost.balanceOf(user)
    print("ZAP YVBOOST --> LP VAULT\n")
    print_balances(user, yvLP, crv, yvboost, yveCrv, pool)
    zap.zapYvBOOSTtoLPVault(2e18, 0, user, {"from":user})
    print_balances(user, yvLP, crv, yvboost, yveCrv, pool)
    yvLP_after = yvLP.balanceOf(user)
    yvboost_after = yvboost.balanceOf(user)
    assert yvboost_before > yvboost_after
    assert yvLP_after > yvLP_before

    yvLP_before = yvLP.balanceOf(user)
    yvboost_before = yvboost.balanceOf(user)
    print("ZAP LP VAULT --> YVBOOST\n")
    print_balances(user, yvLP, crv, yvboost, yveCrv, pool)
    zap.zapLPVaultToYvBOOST(1e18, 0, user, {"from":user})
    print_balances(user, yvLP, crv, yvboost, yveCrv, pool)
    yvLP_after = yvLP.balanceOf(user)
    yvboost_after = yvboost.balanceOf(user)
    assert yvboost_before < yvboost_after
    assert yvLP_after < yvLP_before

    chain.revert()

    pool.exchange(0,1,300e18,0,{'from':whale_crv})
    assert False
    
def print_balances(user, yvLP, crv, yvboost, yveCrv, pool):
    print("CRV:", crv.balanceOf(user)/1e18)
    print("yveCRV:", yveCrv.balanceOf(user)/1e18)
    print("yvBOOST:", yvboost.balanceOf(user)/1e18)
    print("yvLP:", yvLP.balanceOf(user)/1e18)
    print("----------\n")