from brownie import accounts, Contract

def test_native_eth(voter):
    a = accounts[0]
    original_bal = a.balance()
    a.transfer(voter, 1e18)
    assert a.balance() < original_bal
    assert voter.balance() > 0
    voter.execute(
        a.address, 
        voter.balance(), 
        b'', 
        {'from':voter.governance()}
    )
    assert a.balance() == original_bal