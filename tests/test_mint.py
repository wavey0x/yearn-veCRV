from itertools import filterfalse
import brownie
from brownie import Contract

def test_burn(ycrv, yveCrv, crv, whale_yvecrv, user, gov, accounts):
    amount = 100e18
    before = yveCrv.balanceOf(whale_yvecrv)
    yveCrv.approve(ycrv, amount,{'from':whale_yvecrv})
    ycrv.burn_to_mint(amount,{'from':whale_yvecrv})
    assert before - yveCrv.balanceOf(whale_yvecrv) == amount
    assert yveCrv.balanceOf(ycrv) == amount
    with brownie.reverts():
        ycrv.sweep_yvecrv({'from':ycrv.admin()})
    yveCrv.transfer(ycrv, 1e18,{'from':whale_yvecrv})
    bal_before = yveCrv.balanceOf(gov)
    ycrv.sweep_yvecrv({'from':ycrv.admin()})
    yveCrv.balanceOf(gov) > bal_before

def test_mint(ycrv, yveCrv, crv, whale_crv, user, voter, gov, accounts):
    amount = 100e18
    before = crv.balanceOf(whale_crv)
    before_ycrv = ycrv.balanceOf(whale_crv)
    crv.approve(ycrv, 2**256-1,{'from':whale_crv})
    tx = ycrv.mint(amount,{'from':whale_crv})
    assert before - crv.balanceOf(whale_crv) == amount
    assert ycrv.balanceOf(whale_crv) > before_ycrv
    ycrv.transfer(gov, ycrv.balanceOf(whale_crv),{'from':whale_crv})

def test_sweep(ycrv, yveCrv, crv, whale_yvecrv, user, gov, accounts):
    with brownie.reverts():
        ycrv.sweep_yvecrv({'from':ycrv.admin()})
    yveCrv.transfer(ycrv, 1e18,{'from':whale_yvecrv})
    bal_before = yveCrv.balanceOf(gov)
    ycrv.sweep_yvecrv({'from':ycrv.admin()})
    yveCrv.balanceOf(gov) > bal_before

def test_user_no_balance(ycrv, yveCrv, crv, whale_yvecrv, gov, accounts):
    user = accounts[2] # No yveCRV balance
    amount = 100e18
    before = yveCrv.balanceOf(ycrv)
    yveCrv.approve(ycrv, amount,{'from':user})
    with brownie.reverts():
        ycrv.burn_to_mint(amount,{'from':user})
    assert ycrv.balanceOf(user) == 0
    assert before == yveCrv.balanceOf(ycrv)