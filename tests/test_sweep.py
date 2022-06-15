import brownie

def test_sweep(Strategy, live_strat, strategist, ymechs_safe, gov, vault, strategy, trade_factory, token, amount, weth, weth_amount):
    new_strategy = strategist.deploy(Strategy, vault)
    vault.migrateStrategy(live_strat, new_strategy, {"from":gov})
    trade_factory.grantRole(trade_factory.STRATEGY(), new_strategy.address, {"from": ymechs_safe, "gas_price": "0 gwei"})
    new_strategy.setTradeFactory(trade_factory.address, {"from": gov})
    strategy = new_strategy
    # Strategy want token doesn't work
    token.transfer(strategy, amount, {"from": gov})
    assert token.address == strategy.want()
    assert token.balanceOf(strategy) > 0
    with brownie.reverts("!want"):
        strategy.sweep(token, {"from": gov})

    # Vault share token doesn't work
    with brownie.reverts("!shares"):
        strategy.sweep(vault.address, {"from": gov})

    before_balance = weth.balanceOf(gov)
    weth.transfer(strategy, weth_amount, {"from": gov})
    assert weth.address != strategy.want()
    assert weth.balanceOf(gov) == before_balance - weth_amount
    strategy.sweep(weth, {"from": gov})
    assert weth.balanceOf(gov) == before_balance