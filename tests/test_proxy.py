import math, time, brownie
from brownie import Contract


def test_proxy(accounts, live_strat, voter, token, new_proxy, whale_yvecrv, vault, 
    strategy, strategist, amount, user, crv3, chain, whale_3crv, gov):
    new_proxy
    locker = accounts[2]
    new_proxy.approveLocker(locker,{'from':gov})
    vecrv = Contract(new_proxy.veCRV())
    lock_end = vecrv.locked__end(voter)

    new_proxy.maxLock({'from':gov})
    assert vecrv.locked__end(voter) > lock_end

    chain.undo(1)
    new_proxy.maxLock({'from':locker})
    assert vecrv.locked__end(voter) > lock_end

    chain.undo(1)
    new_proxy.revokeLocker(locker,{'from':gov})
    with brownie.reverts("!locker"):
        new_proxy.maxLock({'from':locker})

    # Test voting from voter approved account
    gauge = '0x8Fa728F393588E8D8dD1ca397E9a710E53fA553a'
    new_proxy.vote(gauge,0, {'from':gov})
    chain.undo(1)

    with brownie.reverts("!voter"):
        new_proxy.vote(gauge,0, {'from':voter})
    
    voter = locker
    tx = new_proxy.approveVoter(voter,{'from':gov})
    assert tx.events['VoterApproved']['voter'] == voter
    new_proxy.vote(gauge,0, {'from':voter})
    
    tx = new_proxy.revokeVoter(voter,{'from':gov})
    assert tx.events['VoterRevoked']['voter'] == voter

    with brownie.reverts("!voter"):
        new_proxy.vote(gauge,0, {'from':voter})