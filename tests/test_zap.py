import math, time
from brownie import Contract
import time

def test_zap(zap, Strategy, accounts, voter, whale_crv, token, yveCrv, yvboost, crv, whale_yvecrv, vault, strategy, strategist, amount, user, crv3, chain, whale_3crv, gov):
    crv.approve(zap, 2**256-1, {"from": user})
    yvboost.approve(zap, 2**256-1, {"from": user})
    yveCrv.approve(zap, 2**256-1, {"from": user})
    
    zap.zapCRVtoYvBOOST(500e18, 0, user, {"from":user})