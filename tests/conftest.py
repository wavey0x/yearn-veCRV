import pytest, requests
from brownie import ZERO_ADDRESS, accounts, config, Zap, Contract, interface, Strategy, StrategyProxy, BalancerYBALVoter, yBAL, web3, chain

USE_TENDERLY = False

# This causes test not to re-run fixtures on each run
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

@pytest.fixture(scope="module", autouse=USE_TENDERLY)
def tenderly_fork(web3, chain):
    fork_base_url = "https://simulate.yearn.network/fork"
    payload = {"network_id": str(chain.id)}
    resp = requests.post(fork_base_url, headers={}, json=payload)
    fork_id = resp.json()["simulation_fork"]["id"]
    fork_rpc_url = f"https://rpc.tenderly.co/fork/{fork_id}"
    print(fork_rpc_url)
    tenderly_provider = web3.HTTPProvider(fork_rpc_url, {"timeout": 600})
    web3.provider = tenderly_provider
    print(f"https://dashboard.tenderly.co/yearn/yearn-web/fork/{fork_id}")

@pytest.fixture(scope="session")
def using_tenderly():
    yield USE_TENDERLY

@pytest.fixture
def gov(accounts, weth):
    yield accounts.at("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52", force=True)
    #yield accounts.at("0x6AFB7c9a6E8F34a3E0eC6b734942a5589A84F44C", force=True)

@pytest.fixture
def zap():
    zap = accounts[0].deploy(Zap)
    yield zap

@pytest.fixture
def usdt():
    whale = accounts.at('0x47ac0Fb4F2D84898e4D9E7b4DaB3C24507a6D503', force=True)
    token = Contract('0xdAC17F958D2ee523a2206206994597C13D831ec7')
    token.transfer(accounts[0], 100e6, {'from':whale})
    yield token

@pytest.fixture
def input_tokens(zap):
    input_tokens = []
    for i in range(0,20):
        try:
            t = zap.INPUT_TOKENS(i)
            input_tokens.append(t)
        except:
            break
    
    for i in range(0,20):
        try:
            t = zap.OUTPUT_TOKENS(i)
            input_tokens.append(t)
        except:
            break
    yield input_tokens

@pytest.fixture
def output_tokens(zap):
    output_tokens = []
    for i in range(0,20):
        try:
            t = zap.OUTPUT_TOKENS(i)
            output_tokens.append(t)
        except:
            break
    
    yield output_tokens

@pytest.fixture
def user(accounts, balweth, whale_balweth, zap, bal, weth):
    user = accounts[0]
    bal_whale = accounts.at('0xBA12222222228d8Ba445958a75a0704d566BF2C8', force=True)
    weth_whale = accounts.at('0xF04a5cC80B1E94C69B48f5ee68a08CD2F09A7c3E',force=True)

    balweth.transfer(user, 500_000e18,{'from':whale_balweth})


    bal.transfer(user, 500e18,{'from':bal_whale})
    weth.transfer(user, 5000e18,{'from':weth_whale})
    weth.approve(zap, 2**256-1, {'from': user})
    balweth.approve(zap, 2**256-1, {'from': user})
    bal.approve(zap, 2**256-1, {'from': user})
    yield user

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
def authorizer(accounts):
    yield accounts.at("0x10a19e7ee7d7f8a52822f6817de8ea18204f2e4f", force=True) #balancer dao multisig

@pytest.fixture
def rando(accounts):
    yield accounts[6]

# currently yvecrv token
@pytest.fixture
def token():
    token_address = "0xc5bDdf9843308380375a611c18B50Fb9341f502A"  # this should be the address of the ERC-20 used by the strategy/vault
    yield Contract(token_address)

@pytest.fixture
def pool():
    yield Contract('0x616D4D131F1147aC3B3C3CC752BAB8613395B2bB')

@pytest.fixture
def vebal():
    vebal = "0xC128a9954e6c874eA3d62ce62B468bA073093F25"  # veBAL addr
    yield Contract(vebal)

@pytest.fixture
def name():
    yield "BalancerYBALVoter"

@pytest.fixture
def bal():
    # w = accounts.at('0x10A19e7eE7d7F8a52822f6817de8ea18204F2e4f', force=True)
    # bal.transfer(a, 10_000e18, {'from':w})
    yield Contract("0xba100000625a3754423978a60c9317c58a424e3D")

@pytest.fixture
def bbausd():
    yield Contract("0xA13a9247ea42D743238089903570127DdA72fE44")

@pytest.fixture
def balweth():
    yield Contract("0x5c6Ee304399DBdB9C8Ef030aB642B10820DB8F56")

# @pytest.fixture
# def cvxcrv():
#     yield Contract("0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7")

# @pytest.fixture
# def whale_cvxcrv(accounts):
#     yield accounts.at("0x3Fe65692bfCD0e6CF84cB1E7d24108E434A7587e", force=True)

@pytest.fixture
def smart_wallet_checker():
    yield Contract("0x7869296Efd0a76872fEE62A058C8fBca5c1c826C")

@pytest.fixture
def amount(accounts, token, gov):
    amount = 100 * 10 ** token.decimals()
    # In order to get some funds for the token you are about to use,
    # it impersonate an exchange address to use it's funds.
    reserve = accounts.at("0x9d409a0A012CFbA9B15F6D4B36Ac57A46966Ab9a", force=True)
    token.transfer(accounts[0], amount*2, {"from": reserve})
    token.transfer(gov, amount, {"from": reserve})
    yield amount


@pytest.fixture
def vault(pm, gov, rewards, guardian, management, token):

    yield vault

@pytest.fixture
def eth_whale(accounts):
    yield accounts.at("0x53d284357ec70cE289D6D64134DfAc8E511c8a3D", force=True)

@pytest.fixture
def balancer_vault(accounts):
    yield Contract('0xBA12222222228d8Ba445958a75a0704d566BF2C8')

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
def ybal(strategist):
    yield Contract('0x98E86Ed5b0E48734430BfBe92101156C75418cad')

@pytest.fixture
def vault_abi():
    return Contract("0x9d409a0A012CFbA9B15F6D4B36Ac57A46966Ab9a").abi #yvBOOST

@pytest.fixture
def lp_ybal():
    yield Contract('0x640D2a6540F180aaBa2223480F445D3CD834788B')

@pytest.fixture
def st_ybal():
    yield Contract('0xc09cfb625e586B117282399433257a1C0841edf3')
    # registry = Contract(web3.ens.resolve("v2.registry.ychad.eth"))
    # address = registry.newVault(ybal,gov,gov,"Staked YBAL","st-YBAL",0,{'from':gov}).return_value
    # v = Contract.from_abi("pool", address, vault_abi)
    # v.setDepositLimit(100e25, {'from':gov})
    # balweth.approve(ybal, 2**256-1, {'from':user})
    # ybal.mint(101e18, {'from':user})
    # ybal.approve(v, 2**256-1, {'from':user})
    # v.deposit(100e18,{'from':user})
    # ybal.transfer(v, 1e18,{'from':user}) # Increase pps a bit
    # yield v


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

# @pytest.fixture
# def voter(strategist, gov, smart_wallet_checker, authorizer, vebal, balweth, name):
#     v = strategist.deploy(BalancerYBALVoter)
#     gov = accounts.at('0x36666EC6315E9606f03fc6527E396B95bcA4D384', force=True)
#     v.initialize(vebal, balweth, name, {'from':gov})
#     v.setGovernance(gov, {'from':gov})
#     smart_wallet_checker.allowlistAddress(v, {"from": authorizer}) # balancer to whitelist our voter
#     yield v

@pytest.fixture
def voter(smart_wallet_checker, authorizer):
    v = Contract("0xBA11E7024cbEB1dd2B401C70A83E0d964144686C")
    # smart_wallet_checker.allowlistAddress(v, {"from": authorizer}) # balancer to whitelist our voter
    yield v

@pytest.fixture
def new_proxy(st_strategy, strategist, gov, voter):
    # yield Contract(web3.ens.resolve('curve-proxy.ychad.eth'))
    p = strategist.deploy(StrategyProxy)
    # Set up new proxy
    p.setGovernance(gov)
    p.setFeeRecipient(st_strategy, {"from": gov}) # StrategyStYBAL
    voter.setStrategy(p, {"from": gov})
    st_strategy.setProxy(p, {"from": gov})
    yield p

@pytest.fixture
def fee_distributor(token):
    yield Contract('0xD3cf852898b21fc233251427c2DC93d3d604F3BB')


@pytest.fixture
def whale_eth(accounts):
    yield accounts.at("0x73BCEb1Cd57C711feaC4224D062b0F6ff338501e", force=True)

@pytest.fixture
def whale_bbausd(accounts):
    yield accounts.at("0xBA12222222228d8Ba445958a75a0704d566BF2C8", force=True)

@pytest.fixture
def whale_bal(accounts):
    yield accounts.at("0x10A19e7eE7d7F8a52822f6817de8ea18204F2e4f", force=True)

@pytest.fixture
def whale_balweth(accounts):
    yield accounts.at("0xBA12222222228d8Ba445958a75a0704d566BF2C8", force=True)

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
