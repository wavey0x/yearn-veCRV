from typing import List, Union
from web3 import HTTPProvider
from brownie import (
    Contract,
    accounts,
    ZERO_ADDRESS,
    chain,
    web3,
    history,
    interface,
    Wei,
    ZERO_ADDRESS,
)

def main():
    bal_vault = Contract("0xBA12222222228d8Ba445958a75a0704d566BF2C8")
    balweth = Contract("0x5c6Ee304399DBdB9C8Ef030aB642B10820DB8F56")
    aurabal = Contract("0x616e8BfA43F920657B3497DBf40D6b1A02D4608d")
    zap = accounts.at("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52", force=True) # gov for now
    pool_id = 0x3dd0843a028c86e0b760b1a76929d1c5ef93a2dd000200000000000000000249 # aurabal pool
    kind = 0
    swaps = [(pool_id, 0, 1, 1e18, 0)]
    assets = [balweth, aurabal]
    funds = [zap, True, zap, True]
    print(bal_vault.queryBatchSwap.call(kind, swaps, assets, funds, {'from':zap}))
    _, output = bal_vault.queryBatchSwap.call(kind, swaps, assets, funds, {'from':zap})
    print(output)
    output_amount = output * -1
    print(output_amount / 1e18)