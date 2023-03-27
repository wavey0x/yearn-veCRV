import brownie

def test_sweep(Strategy, live_strat, user, ymechs_safe, gov, st_strategy, st_ybal, trade_factory, token, amount, weth, weth_amount, ybal):
    trade_factory.grantRole(trade_factory.STRATEGY(), st_strategy.address, {"from": ymechs_safe, "gas_price": "0 gwei"})
    st_strategy.setTradeFactory(trade_factory.address, {"from": gov})
    strategy = st_strategy
    token = ybal

    token.mint(amount, {'from':user})
    token.transfer(strategy, amount, {"from": user})
    assert token.address == strategy.want()
    assert token.balanceOf(strategy) > 0
    with brownie.reverts("!want"):
        strategy.sweep(token, {"from": gov})

    # Vault share token doesn't work
    with brownie.reverts("!shares"):
        strategy.sweep(st_ybal.address, {"from": gov})

    before_balance = weth.balanceOf(gov)
    weth.transfer(strategy, weth_amount, {"from": gov})
    assert weth.address != strategy.want()
    assert weth.balanceOf(gov) == before_balance - weth_amount
    strategy.sweep(weth, {"from": gov})
    assert weth.balanceOf(gov) == before_balance