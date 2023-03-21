from brownie import Contract, accounts, web3

def main():
    wavey = accounts.load('wavey')
    pool = Contract("0x7E46fd8a30869aa9ed55af031067Df666EfE87da",owner=wavey)
    vault = Contract("0x2E919d27D515868f3D5Bc9110fa738f9449FC6ad", owner=wavey)
    crv = Contract(pool.coins(0),owner=wavey)
    yvecrv = Contract(pool.coins(1),owner=wavey)
    crv.approve(pool, 2**256-1)
    yvecrv.approve(pool, 2**256-1)
    pool.add_liquidity(
        [crv.balanceOf(wavey),yvecrv.balanceOf(wavey)],
        0
    )

    # Clone vault
    registry = Contract(web3.ens.resolve('v2.registry.ychad.eth'))