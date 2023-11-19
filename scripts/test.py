import math, time, brownie
from brownie import Contract, accounts
import time

def main():
    crv_whale = accounts.at('0x5f3b5DfEb7B28CDbD7FAba78963EE202a494e2A2', force=True)
    ycrv_pool = Contract('0x99f5aCc8EC2Da2BC0771c32814EFF52b712de1E5', owner=crv_whale)
    crv = Contract(ycrv_pool.coins(0), owner=crv_whale)
    ycrv = Contract(ycrv_pool.coins(1), owner=crv_whale)
    crv.approve(ycrv_pool, 2**256-1)
    crv.approve(ycrv, 2**256-1)
    ycrv.approve(ycrv_pool, 2**256-1)

    ycrv_bal = ycrv.mint(crv.balanceOf(crv_whale)/2).return_value
    crv_bal = crv.balanceOf(crv_whale)

    # Make pool imbalanced
    ycrv_pool.add_liquidity([0, 3_000_000e18], 0)

    # Estimate and deposit
    amount_to_deposit = 7_000e18
    expected_amount = ycrv_pool.calc_token_amount([0,amount_to_deposit], True)
    tx = ycrv_pool.add_liquidity([0, amount_to_deposit],0)
    actual_amount = tx.return_value
    diff = abs(actual_amount - expected_amount)

    print(f'Expected: {expected_amount/1e18}')
    print(f'Actual: {actual_amount/1e18}')
    print(f'Percent diff: {diff / actual_amount * 100:,.4f}%')
