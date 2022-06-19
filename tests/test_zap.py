import math, time
from brownie import Contract
import time

def test_zap(zap, pool, Strategy, accounts, voter, yvLP, whale_crv, token, yveCrv, yvboost, crv, whale_yvecrv, vault, strategy, strategist, amount, user, crv3, chain, whale_3crv, gov):
    crv.approve(zap, 2**256-1, {"from": user})
    yvboost.approve(zap, 2**256-1, {"from": user})
    yveCrv.approve(zap, 2**256-1, {"from": user})
    yvLP.approve(zap, 2**256-1, {"from": user})
    
    crv_before = crv.balanceOf(user)
    yv_before = yvLP.balanceOf(user)
    zap.zapCRVtoLPVault(2e18, 0, user, {"from":user})
    crv_after = crv.balanceOf(user)
    yv_after = yvLP.balanceOf(user)
    assert yv_after > yv_before
    assert crv_before > crv_after

    crv_before = crv.balanceOf(user)
    yvboost_before = yvboost.balanceOf(user)
    zap.zapCRVtoYvBOOST(2e18, 0, user, {"from":user})
    crv_after = crv.balanceOf(user)
    yvboost_after = yvboost.balanceOf(user)
    assert yvboost_after > yvboost_before
    assert crv_before > crv_after

    yvLP_before = yvLP.balanceOf(user)
    yvboost_before = yvboost.balanceOf(user)
    zap.zapYvBOOSTtoLPVault(2e18, 0, user, {"from":user})
    yvLP_after = yvLP.balanceOf(user)
    yvboost_after = yvboost.balanceOf(user)
    assert yvboost_before > yvboost_after
    assert yvLP_after > yvLP_before

    yvLP_before = yvLP.balanceOf(user)
    yvboost_before = yvboost.balanceOf(user)
    zap.zapLPVaultToYvBOOST(1e18, 0, user, {"from":user})
    yvLP_after = yvLP.balanceOf(user)
    yvboost_after = yvboost.balanceOf(user)
    assert yvboost_before < yvboost_after
    assert yvLP_after < yvLP_before

    # pool.exchange(0,1,2e18,0,{'from':user})
    