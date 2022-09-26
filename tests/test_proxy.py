import math, time, brownie
from brownie import Contract


def test_proxy(accounts, live_strat, voter, token, new_proxy, whale_yvecrv, vault, fee_distributor, 
    strategy, strategist, amount, user, crv3, chain, whale_3crv, gov):
    WEEK = 60 * 60 * 24 * 7
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
    
    voter_user = locker
    tx = new_proxy.approveVoter(voter_user,{'from':gov})
    assert tx.events['VoterApproved']['voter'] == voter_user
    new_proxy.vote(gauge,0, {'from':voter_user})
    
    tx = new_proxy.revokeVoter(voter_user,{'from':gov})
    assert tx.events['VoterRevoked']['voter'] == voter_user

    with brownie.reverts("!voter"):
        new_proxy.vote(gauge,0, {'from':voter_user})

    crv3.transfer(fee_distributor, 100_000e18, {'from':whale_3crv})
    chain.sleep(WEEK)
    chain.mine()
    y = accounts.at(new_proxy.feeRecipient(),force=True)
    admin = accounts.at(fee_distributor.admin(),force=True)
    fee_distributor.checkpoint_token({'from':admin})
    tx = new_proxy.claim(new_proxy,{'from':y})
    assert False