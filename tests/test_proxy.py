import math, time, brownie
from brownie import Contract, web3, StrategyProxy, ZERO_ADDRESS


def test_proxy(accounts, live_strat, voter, token, new_proxy, whale_yvecrv, vault, fee_distributor, 
    strategy, strategist, amount, user, crv3, chain, whale_3crv, gov):
    WEEK = 60 * 60 * 24 * 7
    max = chain.time() + (365 * 60 * 60 * 24 * 4)
    locker = accounts[2]
    new_proxy.approveLocker(locker,{'from':gov})
    vecrv = Contract(new_proxy.veCRV())
    lock_end = vecrv.locked__end(voter)

    new_proxy.maxLock({'from':gov})
    if int(max/WEEK)*WEEK == lock_end:
        assert vecrv.locked__end(voter) == lock_end
        chain.sleep(60*60*24*7)
        chain.mine()
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

def test_approve_adapter(accounts, live_strat, voter, token, new_proxy, whale_yvecrv, vault, fee_distributor, 
    strategy, strategist, amount, user, crv3, chain, whale_3crv, gov):
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
        '0xD533a949740bb3306d119CC777fa900bA034cd52': {
            'name': 'CRV',
            'should_succeed': False,
        },
        '0xdBdb4d16EdA451D0503b854CF79D55697F90c8DF': {
            'name': 'ALCX',
            'should_succeed': True,
        },
        '0x1E212e054d74ed136256fc5a5DDdB4867c6E003F': {
            'name': '3EURpool-f Gauge',
            'should_succeed': False,
        },
        '0xd662908ADA2Ea1916B3318327A97eB18aD588b5d': {
            'name': 'a3CRV-f Gauge',
            'should_succeed': False,
        },
        '0x38039dD47636154273b287F74C432Cac83Da97e2': {
            'name': 'ag+ib-EUR-f Gauge',
            'should_succeed': False,
        },
        '0xbFcF63294aD7105dEa65aA58F8AE5BE2D9d0952A': {
            'name': '3CRV gauge',
            'should_succeed': False,
        },
        '0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490': {
            'name': '3CRV token',
            'should_succeed': False,
        },
        '0xbebc44782c7db0a1a60cb6fe97d0b483032ff1c7': {
            'name': '3CRV Pool',
            'should_succeed': True,
        },
        '0x0309a528bba0394dc4a2ce59123c52e317a54604': {
            'name': 'REKT yCRV LP token',
            'should_succeed': False,
        },
        '0x9672D72D5843ca5C6b1E0CC676E106920D6a650E': {
            'name': 'REKT yCRV gauge - not approved',
            'should_succeed': True,
        },
        '0xdcef968d416a41cdac0ed8702fac8128a64241a2': {
            'name': 'FRAXBP Pool',
            'should_succeed': True, # Should succeed since this is the pool address, not LP
        },
        '0x3175df0976dfa876431c2e9ee6bc45b65d3473cc': {
            'name': 'FRAXBP token',
            'should_succeed': False,
        },
        '0xe57180685e3348589e9521aa53af0bcd497e884d': {
            'name': 'DOLA/FRAXBP token+pool',
            'should_succeed': False,
        },
    }
    WEEK = 60 * 60 * 24 * 7
    locker = accounts[2]
    new_proxy = Contract.from_abi('',new_proxy.address,new_proxy.abi,owner=gov)
    new_proxy.approveLocker(locker)
    vecrv = Contract(new_proxy.veCRV())
    lock_end = vecrv.locked__end(voter)
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