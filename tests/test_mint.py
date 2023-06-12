import brownie
from brownie import Contract, chain

def test_burn(ycrv, yveCrv, crv, whale_yvecrv, user, gov, accounts):
    amount = 100e18
    before = yveCrv.balanceOf(whale_yvecrv)
    yveCrv.approve(ycrv, amount,{'from':whale_yvecrv})
    before_ycrv = yveCrv.balanceOf(ycrv)
    ycrv.burn_to_mint(amount,{'from':whale_yvecrv})
    assert before - yveCrv.balanceOf(whale_yvecrv) == amount
    assert yveCrv.balanceOf(ycrv) - before_ycrv == amount
    with brownie.reverts():
        ycrv.sweep_yvecrv({'from':ycrv.sweep_recipient()})
    yveCrv.transfer(ycrv, 1e18,{'from':whale_yvecrv})
    bal_before = yveCrv.balanceOf(gov)
    ycrv.sweep_yvecrv({'from':ycrv.sweep_recipient()})
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

def test_buffer_mint(ycrv, zap, crv, whale_crv, user, voter, gov, accounts):
    amount = 100e18
    before = crv.balanceOf(whale_crv)
    before_ycrv = ycrv.balanceOf(whale_crv)
    crv.approve(zap, 2**256-1,{'from':whale_crv})
    
    zap.set_mint_buffer(499, {'from': gov})
    estimate = zap.calc_expected_out(crv, ycrv, amount)
    tx = zap.zap(crv, ycrv, amount, {'from':whale_crv})
    actual = tx.events['Mint']['value'] # This will fail if not mint
    assert estimate == amount
    assert estimate == actual

    chain.undo(1)

    zap.set_mint_buffer(0, {'from': gov})
    estimate = zap.calc_expected_out(crv, ycrv, amount)
    tx = zap.zap(crv, ycrv, amount, {'from':whale_crv})
    actual = tx.events['TokenExchange']['tokens_bought'] # This will fail if not swap
    assert estimate != amount
    assert estimate == actual

def test_change_proxy(ycrv, yveCrv, crv, whale_crv, user, voter, gov, accounts):
    amount = 100e18
    before = crv.balanceOf(whale_crv)
    before_ycrv = ycrv.balanceOf(whale_crv)
    crv.approve(ycrv, 2**256-1,{'from':whale_crv})
    # Change to broken proxy
    # ycrv.set_proxy(gov,{'from':gov})
    # This function should not revert
    tx = ycrv.mint(amount,{'from':whale_crv})
    assert before - crv.balanceOf(whale_crv) == amount
    assert ycrv.balanceOf(whale_crv) > before_ycrv
    ycrv.transfer(gov, ycrv.balanceOf(whale_crv),{'from':whale_crv})

def test_sweep(ycrv, yveCrv, crv, whale_yvecrv, user, gov, accounts):
    with brownie.reverts():
        ycrv.sweep_yvecrv({'from':ycrv.sweep_recipient()})
    yveCrv.transfer(ycrv, 1e18,{'from':whale_yvecrv})
    bal_before = yveCrv.balanceOf(gov)
    ycrv.sweep_yvecrv({'from':ycrv.sweep_recipient()})
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