import pytest, requests
from brownie import ZERO_ADDRESS, config, Contract, interface, StrategyProxy, yCRV, ZapYCRV, web3, chain

# This causes test not to re-run fixtures on each run
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

# @pytest.fixture(scope="module", autouse=True)
# def tenderly_fork(web3, chain):
#     fork_base_url = "https://simulate.yearn.network/fork"
#     payload = {"network_id": str(chain.id)}
#     resp = requests.post(fork_base_url, headers={}, json=payload)
#     fork_id = resp.json()["simulation_fork"]["id"]
#     fork_rpc_url = f"https://rpc.tenderly.co/fork/{fork_id}"
#     print(fork_rpc_url)
#     tenderly_provider = web3.HTTPProvider(fork_rpc_url, {"timeout": 600})
#     web3.provider = tenderly_provider
#     print(f"https://dashboard.tenderly.co/yearn/yearn-web/fork/{fork_id}")

@pytest.fixture
def gov(accounts):
    yield accounts.at("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52", force=True)
    #yield accounts.at("0x6AFB7c9a6E8F34a3E0eC6b734942a5589A84F44C", force=True)

@pytest.fixture
def yvboost():
    yield Contract("0x9d409a0A012CFbA9B15F6D4B36Ac57A46966Ab9a")

@pytest.fixture
def yveCrv():
    yield Contract("0xc5bDdf9843308380375a611c18B50Fb9341f502A")

@pytest.fixture
def whale_yvboost(accounts):
    yield accounts.at("0x25431341A5800759268a6aC1d3CD91C029D7d9CA", force=True)

@pytest.fixture
def user(accounts, yveCrv, yvboost, crv, whale_yvecrv, whale_crv, whale_yvboost, cvxcrv, whale_cvxcrv):
    crv.transfer(accounts[0], 500e18,{'from':whale_crv})
    yveCrv.transfer(accounts[0], 1_000e18,{'from':whale_yvecrv})
    cvxcrv.transfer(accounts[0], 1_000e18,{'from':whale_cvxcrv})
    yield accounts[0]

@pytest.fixture
def rewards(accounts):
    yield accounts[1]


@pytest.fixture
def guardian(accounts):
    yield accounts[2]


@pytest.fixture
def management(accounts):
    yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)


@pytest.fixture
def strategist(accounts):
    yield accounts.at("0x6AFB7c9a6E8F34a3E0eC6b734942a5589A84F44C", force=True)


@pytest.fixture
def keeper(accounts):
    yield accounts.at("0x13dAda6157Fee283723c0254F43FF1FdADe4EEd6", force=True)


@pytest.fixture
def rando(accounts):
    yield accounts[6]


@pytest.fixture
def token():
    token_address = "0xc5bDdf9843308380375a611c18B50Fb9341f502A"  # this should be the address of the ERC-20 used by the strategy/vault
    yield Contract(token_address)


@pytest.fixture
def crv():
    yield Contract("0xD533a949740bb3306d119CC777fa900bA034cd52")

@pytest.fixture
def cvxcrv():
    yield Contract("0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7")

@pytest.fixture
def whale_cvxcrv(accounts):
    yield accounts.at("0x3Fe65692bfCD0e6CF84cB1E7d24108E434A7587e", force=True)

@pytest.fixture
def amount(accounts, token, gov):
    amount = 10_000 * 10 ** token.decimals()
    # In order to get some funds for the token you are about to use,
    # it impersonate an exchange address to use it's funds.
    reserve = accounts.at("0x9d409a0A012CFbA9B15F6D4B36Ac57A46966Ab9a", force=True)
    token.transfer(accounts[0], amount*2, {"from": reserve})
    token.transfer(gov, amount, {"from": reserve})
    yield amount


@pytest.fixture
def vault(pm, gov, rewards, guardian, management, token):
    yield Contract('0x9d409a0A012CFbA9B15F6D4B36Ac57A46966Ab9a')

@pytest.fixture
def eth_whale(accounts):
    yield accounts.at("0x53d284357ec70cE289D6D64134DfAc8E511c8a3D", force=True)


@pytest.fixture
def trade_factory():
    yield Contract("0x7BAF843e06095f68F4990Ca50161C2C4E4e01ec6")

@pytest.fixture
def ymechs_safe():
    yield Contract("0x2C01B4AD51a67E2d8F02208F54dF9aC4c0B778B6")


@pytest.fixture
def sushi_swapper(trade_factory, ymechs_safe):
    yield Contract("0x55dcee9332848AFcF660CE6a2116D83Dd7a71B60")


@pytest.fixture
def live_strat():
    live_strat = Contract('0x7fe508eE30316e3261079e2C81f4451E0445103b')
    yield live_strat

@pytest.fixture
def ycrv(strategist):
    yield strategist.deploy(yCRV)

@pytest.fixture
def vault_abi():
    return Contract("0x9d409a0A012CFbA9B15F6D4B36Ac57A46966Ab9a").abi

@pytest.fixture
def st_ycrv(strategist, ycrv, gov, yveCrv,vault_abi, user):
    registry = Contract(web3.ens.resolve("v2.registry.ychad.eth"))
    address = registry.newVault(ycrv,gov,gov,"Staked YCRV","st-YCRV",{'from':gov}).return_value
    v = Contract.from_abi("pool", address, vault_abi)
    v.setDepositLimit(100e25, {'from':gov})
    ycrv.approve(v, 2**256-1, {'from':user})
    yveCrv.approve(ycrv, 2**256-1, {'from':user})
    ycrv.burn_to_mint(101e18, {'from':user})
    v.deposit(100e18,{'from':user})
    ycrv.transfer(v, 1e18,{'from':user}) # Increase pps a bit
    yield v

@pytest.fixture
def pool(strategist, gov, ycrv, yveCrv, vault_abi, crv, user):
    factory = Contract('0xb9fc157394af804a3578134a6585c0dc9cc990d4', owner=strategist)
    name = 'Yearn CRV'
    symbol = 'yCRV'
    coins = [
        '0xD533a949740bb3306d119CC777fa900bA034cd52',
        ycrv.address,
        ZERO_ADDRESS,
        ZERO_ADDRESS
    ]
    a = 50
    fee = 15000000
    asset_type = 3
    implementation_index = 3
    pool_address = factory.deploy_plain_pool(
        name, 
        symbol, 
        coins, 
        a, 
        fee, 
        asset_type, 
        implementation_index
    ).return_value
    pool = Contract.from_abi("pool", pool_address, Contract("0x7E46fd8a30869aa9ed55af031067Df666EfE87da").abi)
    yveCrv.approve(ycrv,2**256-1, {'from':user})
    ycrv.approve(pool, 2**256-1, {'from':user})
    crv.approve(pool, 2**256-1, {'from':user})
    ycrv.burn_to_mint(yveCrv.balanceOf(user)/2, {'from':user})
    amounts = [105e18, 209e18]
    pool.add_liquidity(amounts, chain.time(),{'from': user})
    yield pool

@pytest.fixture
def lp_ycrv(gov, pool, ycrv, user, vault_abi):
    registry = Contract(web3.ens.resolve("v2.registry.ychad.eth"))
    tx = registry.newVault(pool,gov,gov,"LP YCRV","lp-YCRV",{'from':gov})
    vault_address = tx.events['NewVault']['vault']
    v = Contract.from_abi("vault", vault_address, vault_abi)
    v.setDepositLimit(100e25, {'from':gov})
    pool.approve(v, 2**256-1,{'from':user})
    v.deposit({'from':user})
    ycrv.transfer(v, 1e17,{'from':user}) # Increase pps a bit
    yield v

@pytest.fixture
def zap(ycrv, strategist, st_ycrv, lp_ycrv, pool):
    z = strategist.deploy(ZapYCRV)
    yield z

@pytest.fixture
def strategy(strategist, live_strat, 
    keeper, vault, Strategy, gov, token, crv3, usdc,
    trade_factory, ymechs_safe
    ):

    live_strat.setDoHealthCheck(False, {"from": gov})

    new_strategy = strategist.deploy(Strategy, vault)
    tx = vault.migrateStrategy(live_strat, new_strategy, {"from":gov})

    new_strategy.setKeeper(keeper, {"from":gov})

    trade_factory.grantRole(trade_factory.STRATEGY(), new_strategy.address, {"from": ymechs_safe, "gas_price": "0 gwei"})
    new_strategy.setTradeFactory(trade_factory.address, {"from": gov})

    yield new_strategy


@pytest.fixture
def crv3():
    yield Contract("0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490")


@pytest.fixture
def usdc():
    yield Contract("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")


@pytest.fixture
def weth():
    yield Contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")


@pytest.fixture
def old_proxy(strategy, gov):
    p = Contract("0x9a165622a744C20E3B2CB443AeD98110a33a231b")
    #p.approveStrategy(strategy.address, strategy.address, {"from":gov}) # Self address as gauge
    yield p



@pytest.fixture
def voter():
    yield Contract("0xF147b8125d2ef93FB6965Db97D6746952a133934")

@pytest.fixture
def new_proxy(strategy, yveCrv, strategist, gov, voter):
    # yield Contract(web3.ens.resolve('curve-proxy.ychad.eth'))
    p = strategist.deploy(StrategyProxy)
    # Set up new proxy
    p.setGovernance(gov)
    p.setFeeRecipient(strategy, {"from": gov})
    voter.setStrategy(p, {"from": gov})
    strategy.setProxy(p, {"from": gov})
    yveCrv.setProxy(p, {"from": gov})
    yveCrv.setFeeDistribution(ZERO_ADDRESS, {"from": gov})
    yield p

@pytest.fixture
def yveCrv(token):
    yield token

@pytest.fixture
def fee_distributor(token):
    yield Contract('0xA464e6DCda8AC41e03616F95f4BC98a13b8922Dc')


@pytest.fixture
def whale_eth(accounts):
    yield accounts.at("0x73BCEb1Cd57C711feaC4224D062b0F6ff338501e", force=True)

@pytest.fixture
def whale_yvecrv(accounts):
    yield accounts.at("0x10B47177E92Ef9D5C6059055d92DdF6290848991", force=True)

@pytest.fixture
def whale_3crv(accounts):
    yield accounts.at("0x43b4FdFD4Ff969587185cDB6f0BD875c5Fc83f8c", force=True)

@pytest.fixture
def whale_crv(accounts):
    yield accounts.at("0x5f3b5DfEb7B28CDbD7FAba78963EE202a494e2A2", force=True)

@pytest.fixture
def sushiswap_crv(accounts):
    yield accounts.at("0x5c00977a2002a3C9925dFDfb6815765F578a804f", force=True)


@pytest.fixture
def sushiswap(Contract):
    yield Contract("0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F")

# @pytest.fixture
# def pool(accounts, crv, yveCrv, user):
#     pool = Contract("0x7E46fd8a30869aa9ed55af031067Df666EfE87da")
#     yveCrv.approve(pool, 2**256-1, {'from':user})
#     crv.approve(pool, 2**256-1, {'from':user})
#     # pool.add_liquidity([100e18,100e18], 0, user, {'from':user})
#     yield pool

@pytest.fixture
def not_banteg(accounts):
    yield accounts.at("0x0035Fc5208eF989c28d47e552E92b0C507D2B318", force=True)

@pytest.fixture
def klim(accounts):
    yield accounts.at("0x279a7DBFaE376427FFac52fcb0883147D42165FF", force=True) # airdropper

@pytest.fixture
def weth_amount(accounts, weth, gov):
    amount = 1e21
    # In order to get some funds for the token you are about to use,
    # it impersonate an exchange address to use it's funds.
    reserve = accounts.at("0x2F0b23f53734252Bda2277357e97e1517d6B042A", force=True)
    weth.transfer(gov, amount, {"from": reserve})
    yield amount

@pytest.fixture(scope="session")
def RELATIVE_APPROX():
    yield 1e-5

@pytest.fixture(scope="module")
def multicall_swapper(interface):
    yield interface.MultiCallOptimizedSwapper(
        "0xB2F65F254Ab636C96fb785cc9B4485cbeD39CDAA"
    )

@pytest.fixture(scope="module")
def curvefi_3crv_pool(interface):
    yield interface.CurveFiPool(
        "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"
    )
