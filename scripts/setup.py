from brownie import Contract, accounts, ZERO_ADDRESS, chain, web3

def main():
    wavey = accounts.load('wavey2')
    ybal = Contract('0x98E86Ed5b0E48734430BfBe92101156C75418cad', owner=wavey)

    factory = Contract('0xfADa0f4547AB2de89D1304A668C39B3E09Aa7c76', owner=wavey)

    tx = factory.create(
        'Balancer yBAL Stable Pool',    # name
        'B-yBAL-STABLE',               # symbol
        [
            '0x5c6Ee304399DBdB9C8Ef030aB642B10820DB8F56', # 80/20
            '0x98E86Ed5b0E48734430BfBe92101156C75418cad'  # yBAL
        ],                              # tokens
        30,                             # amplificationParameter,
        [ZERO_ADDRESS, ZERO_ADDRESS],   # rateProviders,
        [0,0],                          # tokenRateCachDuration,
        [False, False],                 # exemptFromYieldProtocolFeeFlags,
        2e15,                           # swapFeePercentage
        web3.ens.resolve('ychad.eth'),  # owner
        0                               # salt
    )

    print()
    pool = tx.events['PoolCreated']['pool']
    print(f'{pool}')
    chain.reset()

    pool = Contract('0xD61e198e139369a40818FE05F5d5e6e045Cd6eaF')
    gauge_factory = Contract('0x4E7bBd911cf1EFa442BC1b2e9Ea01ffE785412EC', owner=wavey)
    tx = gauge_factory.create('0xD61e198e139369a40818FE05F5d5e6e045Cd6eaF')
    r = Contract(web3.ens.resolve('v2.registry.ychad.eth'))
    release_registry = Contract(r.releaseRegistry())
    release_registry.newVault(
        pool,
        wavey,
        wavey,
        web3.ens.resolve('treasury.ychad.eth'),
        'LP Yearn BAL Vault',
        'lp-yBAL',
        0
    )