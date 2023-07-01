
import math, time, brownie
from re import A
from brownie import Contract, accounts
import time

def test_zap(zap, pool, strategist, pool_v1, pool_v2, lp_ycrv, lp_ycrv_v1, amount, user, crv3, cvxcrv, whale_cvxcrv, chain, whale_crv, whale_3crv, gov, st_ycrv, ycrv, yvboost, yveCrv, crv):
    yveCrv.approve(ycrv,2**256-1, {'from':user})
    ycrv.burn_to_mint(yveCrv.balanceOf(user)/2, {'from':user})
    crv.approve(zap, 2**256-1, {"from": user})
    crv.approve(pool, 2**256-1, {"from": whale_crv})
    yvboost.approve(zap, 2**256-1, {"from": user})
    yveCrv.approve(zap, 2**256-1, {"from": user})
    lp_ycrv_v1.approve(zap, 2**256-1, {"from": user})
    lp_ycrv.approve(zap, 2**256-1, {"from": user})
    st_ycrv.approve(zap, 2**256-1, {"from": user})
    pool_v1.approve(zap, 2**256-1, {"from": user})
    pool_v2.approve(zap, 2**256-1, {"from": user})
    cvxcrv.approve(zap, 2**256-1, {"from": user})
    ycrv.approve(zap, 2**256-1, {"from": user})
    pool.approve(lp_ycrv, 2**256-1, {"from": whale_crv})

    # Make yearn initial deposit
    lp_v1_whale = accounts.at('0x7d2aB9CA511EBD6F03971Fb417d3492aA82513f0', force=True)
    lp_ycrv_v1.approve(zap, 2**256-1, {'from':lp_v1_whale})
    expected = zap.calc_expected_out(lp_ycrv_v1, lp_ycrv, lp_ycrv_v1.balanceOf(lp_v1_whale), {'from':lp_v1_whale})
    out = zap.zap(lp_ycrv_v1, lp_ycrv, lp_ycrv_v1.balanceOf(lp_v1_whale), {'from':lp_v1_whale}).return_value

    print('Yearn Zap')
    print(f'Expected: {expected/1e18}')
    print(f'Actual: {out/1e18}')
    diff = (out-expected) / out * 100
    print(f'Percent off: {diff:,.7f}%')
    # OPTIONALLY use the functions below to affect prices and see outcomes
    # Remember that expected amounts out relies on view-only function
    # While zap relies on write function
    # This can have impact when zap takes a multi-step route, affecting the pool
    # state. The view functions will not be able to account for this, especially when liquidity is low.

    # pump_ycrv_price(lp_ycrv_v1, whale_crv, crv)
    # pump_crv_price(lp_ycrv, whale_crv, ycrv, crv, user)

    chain.snapshot()
    crv_before = crv.balanceOf(user)
    yv_before = lp_ycrv.balanceOf(user)
    print("ZAP CRV --> LP VAULT\n")
    print_user_balances(user, lp_ycrv, crv, yvboost, yveCrv, pool)

    legacy_tokens = []
    output_tokens = []
    try:
        for i in range(0,20):
            legacy_tokens.append(zap.LEGACY_TOKENS(i))
    except:
        pass
    try:
        for i in range(0,20):
            output_tokens.append(zap.OUTPUT_TOKENS(i))
    except:
        pass

    input_tokens = legacy_tokens + output_tokens + [lp_ycrv_v1.token(), lp_ycrv.token()]
    input_tokens.append(crv.address)
    input_tokens.append(cvxcrv.address)
    input_tokens.append(lp_ycrv_v1.address)
    # Test some calls
    amount = 4_000e18
    for i in input_tokens:
        for o in output_tokens:
            if (
                (i == lp_ycrv_v1.address or i == lp_ycrv_v1.token()) 
                and o != lp_ycrv.address
            ):
                continue # v1 can only go directly to v2
            # if i == lp_ycrv and o == ycrv:
            #     tx = zap.calc_expected_out.transact(i, o, amount)
            #     print_results(True,i, o, amount, r, s)
            #     assert False
            r = zap.calc_expected_out(i, o, amount)
            s = zap.relative_price(i, o, amount)
            min = r * 0.99
            actual = 0
            if i == o:
                with brownie.reverts():
                    tx = zap.zap(i, o, amount, r * .99, {'from': user})
                    tx.gas_used
                    actual = tx.return_value
            else:
                tx = zap.zap(i, o, amount, r * .99, {'from': user})
                gas_consumed = tx.gas_used
                actual = tx.return_value
            assert_balances(zap, pool, strategist, lp_ycrv, amount, user, crv3, cvxcrv, whale_cvxcrv, chain, whale_crv, whale_3crv, gov, st_ycrv, ycrv, yvboost, yveCrv, crv)
            print_results(True,i, o, amount, r, s, actual, gas_consumed)



def print_results(is_legacy, i, o, a, r, s, actual, gas_consumed):
    # abi = Contract("0x9d409a0A012CFbA9B15F6D4B36Ac57A46966Ab9a").abi
    i = Contract(i).symbol()
    o = Contract(o).symbol()
    print(f'IN  {i}')
    print(f'OUT {o}')
    print(f'AMT IN  {a/1e18}')
    print(f'VIRT AMT OUT {s/1e18}')
    print(f'EXP AMT OUT {r/1e18}')
    print(f'ACTUAL AMT OUT {actual/1e18}')
    if actual != 0:
        diff = (actual-r) / actual * 100
        print(f'Percent off: {"" if abs(diff) < 0.001 else "❌"} {diff:,.7f}%')
        # if abs(diff) > 1:
        #     assert False
    print(f'⛽️ {gas_consumed:,.2f}')
    print('---')

def pump_crv_price(lp_ycrv, whale_crv, ycrv, crv, user):
    pool = Contract(lp_ycrv.token(), owner=whale_crv)
    crv.approve(ycrv, 2**256-1, {"from": whale_crv})
    ycrv.mint(crv.balanceOf(whale_crv)/2, {'from':whale_crv})
    ycrv.approve(pool, 2**256-1, {"from": whale_crv})
    bal = ycrv.balanceOf(whale_crv)
    assert bal > 50_000e18
    pool.add_liquidity([0,2_000_000e18],0)
    lp_ycrv.deposit({"from": whale_crv})
    lp_ycrv.transfer(user, 10_000e18, {"from": whale_crv})

def pump_ycrv_price(lp_ycrv_v1, whale_crv, crv):
    pool_v1 = Contract(lp_ycrv_v1.token(), owner=whale_crv)
    crv.approve(pool_v1, 2**256-1, {"from": whale_crv})
    pool_v1.add_liquidity([10_000,0],0)

    # zap.zapCRVtoLPVault(2e18, 0, user, {"from":user})
    # print_balances(user, lp_ycrv, crv, yvboost, yveCrv, pool)
    # crv_after = crv.balanceOf(user)
    # yv_after = lp_ycrv.balanceOf(user)
    # assert yv_after > yv_before
    # assert crv_before > crv_after

    # crv_before = crv.balanceOf(user)
    # yvboost_before = yvboost.balanceOf(user)
    # print("ZAP CRV --> YVBOOST\n")
    # print_balances(user, lp_ycrv, crv, yvboost, yveCrv, pool)
    # zap.zapCRVtoYvBOOST(2e18, 0, user, {"from":user})
    # print_balances(user, yvLP, crv, yvboost, yveCrv, pool)
    # crv_after = crv.balanceOf(user)
    # yvboost_after = yvboost.balanceOf(user)
    # assert yvboost_after > yvboost_before
    # assert crv_before > crv_after

    # yvLP_before = yvLP.balanceOf(user)
    # yvboost_before = yvboost.balanceOf(user)
    # print("ZAP YVBOOST --> LP VAULT\n")
    # print_balances(user, yvLP, crv, yvboost, yveCrv, pool)
    # zap.zapYvBOOSTtoLPVault(2e18, 0, user, {"from":user})
    # print_balances(user, yvLP, crv, yvboost, yveCrv, pool)
    # yvLP_after = yvLP.balanceOf(user)
    # yvboost_after = yvboost.balanceOf(user)
    # assert yvboost_before > yvboost_after
    # assert yvLP_after > yvLP_before

    # yvLP_before = yvLP.balanceOf(user)
    # yvboost_before = yvboost.balanceOf(user)
    # print("ZAP LP VAULT --> YVBOOST\n")
    # print_balances(user, yvLP, crv, yvboost, yveCrv, pool)
    # zap.zapLPVaultToYvBOOST(1e18, 0, user, {"from":user})
    # print_balances(user, yvLP, crv, yvboost, yveCrv, pool)
    # yvLP_after = yvLP.balanceOf(user)
    # yvboost_after = yvboost.balanceOf(user)
    # assert yvboost_before < yvboost_after
    # assert yvLP_after < yvLP_before

    # chain.revert()

    # pool.exchange(0,1,300e18,0,{'from':whale_crv})
    # assert False

def print_user_balances(user, yvLP, crv, yvboost, yveCrv, pool):
    print("CRV:", crv.balanceOf(user)/1e18)
    print("yveCRV:", yveCrv.balanceOf(user)/1e18)
    print("yvBOOST:", yvboost.balanceOf(user)/1e18)
    print("yvLP:", yvLP.balanceOf(user)/1e18)
    print("----------\n")

def assert_balances(zap, pool, strategist, lp_ycrv, amount, user, crv3, cvxcrv, whale_cvxcrv, chain, whale_crv, whale_3crv, gov, st_ycrv, ycrv, yvboost, yveCrv, crv):
    assert ycrv.balanceOf(zap) == 0
    assert crv.balanceOf(zap) == 0
    assert yvboost.balanceOf(zap) == 0
    assert yveCrv.balanceOf(zap) == 0
    assert lp_ycrv.balanceOf(zap) == 0
    assert st_ycrv.balanceOf(zap) == 0
    assert cvxcrv.balanceOf(zap) == 0
    assert ycrv.balanceOf(zap) == 0
    assert pool.balanceOf(zap) == 0