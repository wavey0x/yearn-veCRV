from brownie import Contract, accounts

def main():
    wavey = accounts.load('wavey')
    pool = Contract("0x7E46fd8a30869aa9ed55af031067Df666EfE87da",owner=wavey)
    crv = Contract(pool.coins(0),owner=wavey)
    yvecrv = Contract(pool.coins(1),owner=wavey)
    crv.approve(pool, 2**256-1)
    yvecrv.approve(pool, 2**256-1)
    pool.add_liquidity(
        [crv.balanceOf(wavey),yvecrv.balanceOf(wavey)],
        0
    )