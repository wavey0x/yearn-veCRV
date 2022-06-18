import math, time
from brownie import Contract
import time

def test_zap(zap, pool, Strategy, accounts, voter, whale_crv, token, yveCrv, yvboost, crv, whale_yvecrv, vault, strategy, strategist, amount, user, crv3, chain, whale_3crv, gov):
    crv.approve(zap, 2**256-1, {"from": user})
    yvboost.approve(zap, 2**256-1, {"from": user})
    yveCrv.approve(zap, 2**256-1, {"from": user})
    
    # assert False
    crv.transfer(zap,2e18,{'from':user})
    # zap.zapCRVtoYvBOOST(2e18, 0, user, {"from":user})
    zap.zapCRVtoLPVault(2e18, 0, user, {"from":user})
    # pool.exchange(0,1,2e18,0,{'from':user})
    