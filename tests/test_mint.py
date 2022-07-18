import brownie
from brownie import Contract

def test_burn(ycrv, yveCrv, crv, whale_yvecrv, user,gov):
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
