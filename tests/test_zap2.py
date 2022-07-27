import math, time, brownie
from re import A
from brownie import Contract
import time

def test_zap(zap, pool, strategist, lp_ycrv, amount, user, crv3, cvxcrv, whale_cvxcrv, chain, whale_crv, whale_3crv, gov, st_ycrv, ycrv, yvboost, yveCrv, crv):
    ycrv.burn_to_mint(yveCrv.balanceOf(user)/2, {'from':user})
    crv.approve(zap, 2**256-1, {"from": user})
    crv.approve(pool, 2**256-1, {"from": whale_crv})
    yvboost.approve(zap, 2**256-1, {"from": user})
    yveCrv.approve(zap, 2**256-1, {"from": user})
    lp_ycrv.approve(zap, 2**256-1, {"from": user})
    st_ycrv.approve(zap, 2**256-1, {"from": user})
    cvxcrv.approve(zap, 2**256-1, {"from": user})
    ycrv.approve(zap, 2**256-1, {"from": user})
    
    chain.snapshot()
    crv_before = crv.balanceOf(user)
    yv_before = lp_ycrv.balanceOf(user)
    print("ZAP CRV --> LP VAULT\n")
    print_user_balances(user, lp_ycrv, crv, yvboost, yveCrv, pool)
    
    legacy_tokens = []
    output_tokens = []
    try:
        for i in range(0,20):
            legacy_tokens.append(zap.legacy_tokens(i))
    except:
        pass
    try:
        for i in range(0,20):
            output_tokens.append(zap.output_tokens(i))
    except:
        pass
    
    input_tokens = legacy_tokens + output_tokens
    input_tokens.append(crv.address)
    input_tokens.append(cvxcrv.address)
    # Test some calls
    amount = 10e18
    for i in input_tokens:
        for o in output_tokens:
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
                    actual = zap.zap(i, o, amount, r * .99, {'from': user}).return_value
            else:
                actual = zap.zap(i, o, amount, r * .99, {'from': user}).return_value
            print_results(True,i, o, amount, r, s, actual)

    

def print_results(is_legacy, i, o, a, r, s, actual):
    abi = Contract("0x9d409a0A012CFbA9B15F6D4B36Ac57A46966Ab9a").abi
    i = Contract.from_abi("",i,abi).symbol()
    o = Contract.from_abi("",o,abi).symbol()
    print(f'IN  {i}')
    print(f'OUT {o}')
    print(f'AMT IN  {a/1e18}')
    print(f'VIRT AMT OUT {s/1e18}')
    print(f'EXP AMT OUT {r/1e18}')
    print(f'ACTUAL AMT OUT {actual/1e18}')
    print('---')

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