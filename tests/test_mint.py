from itertools import filterfalse
import brownie
from brownie import Contract

def test_mint(ybal, balweth, whale_balweth, gov):
    amount = 100e18
    before = balweth.balanceOf(whale_balweth)
    before_ybal = ybal.balanceOf(whale_balweth)
    balweth.approve(ybal, 2**256-1,{'from':whale_balweth})
    tx = ybal.mint(amount,{'from':whale_balweth})
    assert before - balweth.balanceOf(whale_balweth) == amount
    assert ybal.balanceOf(whale_balweth) == before_ybal + amount
    assert ybal.balanceOf(whale_balweth) > before_ybal
    ybal.transfer(gov, ybal.balanceOf(whale_balweth),{'from':whale_balweth})

def test_sweep(ybal, bal, whale_bal, gov):
    bal.transfer(ybal, 1e18,{'from':whale_bal})
    bal_before = bal.balanceOf(gov)
    ybal.sweep(bal, 1e18,{'from':ybal.sweep_recipient()})
    assert bal.balanceOf(gov) == bal_before + 1e18
    assert bal.balanceOf(gov) > bal_before

def test_user_no_balance(ybal, balweth, accounts):
    user = accounts[2] # No balweth balance
    amount = 100e18
    before = balweth.balanceOf(ybal)
    balweth.approve(ybal, amount,{'from':user})
    with brownie.reverts():
        ybal.mint(amount,{'from':user})
    assert ybal.balanceOf(user) == 0
    assert before == balweth.balanceOf(ybal)