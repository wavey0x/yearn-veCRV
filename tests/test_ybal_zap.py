import math, time, brownie
from re import A
from brownie import Contract, accounts
import time

def test_zap(zap_test, strategist, amount, user, chain, weth, gov, bal, balweth):
    x = accounts.at('0x5041ed759Dd4aFc3a72b8192C143F72f4724081A', force=True)
    
    tx = zap_test.go()
    balweth.balanceOf(zap_test)
    weth.balanceOf(zap_test)