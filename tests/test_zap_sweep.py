import math, time, brownie
from re import A
from brownie import Contract, accounts
import time

def test_zap(zap, pool, strategist, lp_ycrv, amount, user, crv3, cvxcrv, whale_cvxcrv, chain, whale_crv, whale_3crv, gov, st_ycrv, ycrv, yvboost, yveCrv, crv):
    user = accounts.at('0x5041ed759Dd4aFc3a72b8192C143F72f4724081A', force=True)
    usdt = Contract('0xdAC17F958D2ee523a2206206994597C13D831ec7', owner=user)
    usdt.transfer(zap, 100e6)
    assert usdt.balanceOf(zap) == 100e6
    zap.sweep(usdt,{'from':gov})
    assert usdt.balanceOf(zap) == 0