import math, time, brownie
from brownie import Contract, web3, ZERO_ADDRESS


def test_proxy(accounts, voter, new_proxy, fee_distributor, bal, bbausd, balweth, chain, whale_bal, whale_bbausd, gov, user, st_strategy):
    WEEK = 60 * 60 * 24 * 7
    DAY = 60 * 60 * 24
    max = chain.time() + (365 * 60 * 60 * 24)
    locker = accounts[2]
    new_proxy.approveLocker(locker,{'from':gov})
    vebal = Contract(new_proxy.veBAL())

    # createLock = first lock
    balweth.transfer(voter, 1e18,{'from':user})
    voter.createLock(1e18, chain.time() + (28 * 60 * 60 * 24), {'from':gov}) # 1 balweth lp token, for four weeks
    lock_end = vebal.locked__end(voter)
    print('lock_end: ', lock_end) # 23 march 2023
    
    new_proxy.lock({'from':gov})
    print('voter: ', voter)
    print('voter.strategy(): ', voter.strategy())
    print('voter.governance(): ', voter.governance())
    print('new_proxy: ', new_proxy)
    print('new_proxy.governance(): ', new_proxy.governance())
    print('gov: ', gov)
    tx = new_proxy.maxLock({'from':gov}) # issue with safeexecute in voter
    tx.call_trace(True)
    if int(max/WEEK)*WEEK == lock_end:
        assert vebal.locked__end(voter) == lock_end
        chain.sleep(60*60*24*7)
        chain.mine()
        new_proxy.maxLock({'from':gov})
    assert vebal.locked__end(voter) > lock_end

    chain.undo(1)
    new_proxy.maxLock({'from':locker})
    assert vebal.locked__end(voter) > lock_end

    chain.undo(1)
    new_proxy.revokeLocker(locker,{'from':gov})
    with brownie.reverts("!locker"):
        new_proxy.maxLock({'from':locker})

    # Test voting from voter approved account
    gauge = '0x9703C0144e8b68280b97d9e30aC6f979Dd6A38d7' # stg/bbausd
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

    bal.transfer(fee_distributor, 100_000e18, {'from':whale_bal})
    bbausd.transfer(fee_distributor, 100_000e18, {'from':whale_bbausd})
    chain.sleep(WEEK)
    chain.mine()

    bal_balance_before = bal.balanceOf(st_strategy)
    print('bal_balance_before: ', bal_balance_before)
    bbausd_balance_before = bbausd.balanceOf(st_strategy)
    print('bbausd_balance_before: ', bbausd_balance_before)

    # admin = accounts.at(fee_distributor.admin(),force=True)
    # fee_distributor.checkpoint_token({'from':admin})
    new_proxy.claim(st_strategy,{'from':st_strategy})
    
    bal_balance_after = bal.balanceOf(st_strategy)
    print('bal_balance_after: ', bal_balance_after)
    # assert bal_balance_after > bal_balance_before
    bbausd_balance_after = bbausd.balanceOf(st_strategy)
    print('bbausd_balance_after: ', bbausd_balance_after)
    # assert bbausd_balance_after > bbausd_balance_before

    last_time_cursor = new_proxy.lastTimeCursor()
    print("last_time_cursor:" , last_time_cursor)

    #test second claim
    bal.transfer(fee_distributor, 14_327e18, {'from':whale_bal})
    bbausd.transfer(fee_distributor, 100_000e18, {'from':whale_bbausd})
    chain.sleep(last_time_cursor - chain.time())
    chain.mine()
    assert new_proxy.claimable() == False
    chain.sleep((last_time_cursor - chain.time()) + DAY)
    chain.mine()
    assert new_proxy.claimable() == True
    # admin = accounts.at(fee_distributor.admin(),force=True)
    # fee_distributor.checkpoint_token({'from':admin})
    tx = new_proxy.claim(st_strategy,{'from':st_strategy})

    bal_balance_after_2 = bal.balanceOf(st_strategy)
    print('bal_balance_after_2: ', bal_balance_after_2)
    # assert bal_balance_after > bal_balance_before
    bbausd_balance_after_2 = bbausd.balanceOf(st_strategy)
    print('bbausd_balance_after_2: ', bbausd_balance_after_2)
    # assert bbausd_balance_after > bbausd_balance_before

def test_approve_adapter(accounts, voter, new_proxy, bal, bbausd, chain, whale_bal, whale_bbausd, gov):
    # LP tokens are blocked
    # Approved gauge tokens are blocked
    # Pools are only blocked if pool address == lp token address
    TEST_CASES = {
        '0x89Ab32156e46F46D02ade3FEcbe5Fc4243B9AAeD': {
            'name': 'PNT',
            'should_succeed': True,
        },
        '0xBC19712FEB3a26080eBf6f2F7849b417FdD792CA': {
            'name': 'BOR',
            'should_succeed': True,
        },
        '0xba100000625a3754423978a60c9317c58a424e3D': {
            'name': 'BAL',
            'should_succeed': False,
        },
        '0x5c6Ee304399DBdB9C8Ef030aB642B10820DB8F56': {
            'name': 'BALWETH',
            'should_succeed': False,
        },
        '0xA13a9247ea42D743238089903570127DdA72fE44': {
            'name': 'BBAUSD',
            'should_succeed': False,
        },
        '0xA13a9247ea42D743238089903570127DdA72fE44': {
            'name': 'BBAUSD Gauge',
            'should_succeed': False,
        },
        '0xdBdb4d16EdA451D0503b854CF79D55697F90c8DF': {
            'name': 'ALCX',
            'should_succeed': True,
        },
        '0x4ce0BD7deBf13434d3ae127430e9BD4291bfB61f': {
            'name': 'Balancer 50STG-50bb-a-USD Pool',
            'should_succeed': False,
        },
        '0x9703C0144e8b68280b97d9e30aC6f979Dd6A38d7': {
            'name': 'Balancer 50STG-50bb-a-USD Gauge',
            'should_succeed': False,
        },
        '0x3dd0843A028C86e0b760b1A76929d1C5Ef93a2dd': {
            'name': 'Balancer B-auraBAL-STABLE Pool',
            'should_succeed': False,
        },
        '0x0312AA8D0BA4a1969Fddb382235870bF55f7f242': {
            'name': 'Balancer B-auraBAL-STABLE Gauge',
            'should_succeed': False,
        },
        '0x32296969Ef14EB0c6d29669C550D4a0449130230': {
            'name': 'Balancer B-stETH-STABLE Pool',
            'should_succeed': False,
        },
        '0xcD4722B7c24C29e0413BDCd9e51404B4539D14aE': {
            'name': 'Balancer B-stETH-STABLE Gauge',
            'should_succeed': False,
        },
    }
    WEEK = 60 * 60 * 24 * 7
    locker = accounts[2]
    new_proxy = Contract.from_abi('',new_proxy.address,new_proxy.abi,owner=gov)
    new_proxy.approveLocker(locker)
    vebal = Contract(new_proxy.veBAL())
    lock_end = vebal.locked__end(voter)
    for key in TEST_CASES:
        name = TEST_CASES[key]['name']
        should_succeed = TEST_CASES[key]['should_succeed']
        recipient = web3.ens.resolve('ychad.eth')
        print(f'Testing {name}\nExpected to revert {not should_succeed}')
        if not should_succeed:
            with brownie.reverts():
                tx = new_proxy.approveExtraTokenRecipient(key, recipient)
            with brownie.reverts():
                tx = new_proxy.approveRewardToken(key)
        else:
            tx = new_proxy.approveExtraTokenRecipient(key, recipient)
            tx = new_proxy.approveRewardToken(key)
            assert new_proxy.rewardTokenApproved(key) == True
        print(f'Gas used {tx.gas_used:_}')
        # if tx.gas_used > 1_000_000:
        #     assert False
        if new_proxy.extraTokenRecipient(key) != ZERO_ADDRESS:
            tx = new_proxy.revokeExtraTokenRecipient(key)
        if new_proxy.rewardTokenApproved(key):
            tx = new_proxy.revokeRewardToken(key)