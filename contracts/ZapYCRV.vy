# @version 0.3.3

from vyper.interfaces import ERC20
from vyper.interfaces import ERC20Detailed

interface Vault:
    def deposit(amount: uint256, recipient: address = msg.sender) -> uint256: nonpayable
    def withdraw(shares: uint256) -> uint256: nonpayable
    def pricePerShare() -> uint256: view

interface IYCRV:
    def burn_to_mint(amount: uint256, recipient: address = msg.sender): nonpayable

interface Curve:
    def get_virtual_price() -> uint256: view
    def get_dy(i: int128, j: int128, dx: uint256) -> uint256: view
    def exchange(i: int128, j: int128, dx: uint256, min_dy: uint256) -> uint256: nonpayable
    def add_liquidity(amounts: uint256[2], min_mint_amount: uint256) -> uint256: nonpayable
    def remove_liquidity_one_coin(_token_amount: uint256, i: int128, min_amount: uint256): nonpayable
    def calc_token_amount(amounts: uint256[2], deposit: bool) -> uint256: view

event UpdateAdmin:
    admin: indexed(address)

YVECRV: constant(address) =     0xc5bDdf9843308380375a611c18B50Fb9341f502A # YVECRV
CRV: constant(address) =        0xD533a949740bb3306d119CC777fa900bA034cd52 # CRV
YVBOOST: constant(address) =    0x9d409a0A012CFbA9B15F6D4B36Ac57A46966Ab9a # YVBOOST
YCRV: constant(address) =       0xc5bDdf9843308380375a611c18B50Fb9341f502A # YCRV
STYCRV: constant(address) =     0xc5bDdf9843308380375a611c18B50Fb9341f502A # ST-YCRV
POOL: constant(address) =       0xc5bDdf9843308380375a611c18B50Fb9341f502A # LP-YCRV
LPVAULT: constant(address) =    0xc5bDdf9843308380375a611c18B50Fb9341f502A # LP-YCRV

name: public(String[32])
admin: public(address)
legacy_tokens: public(address[2])
output_tokens: public(address[3])

@external
def __init__():
    self.name = "Zap Yearn CRV"
    self.admin = 0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52
    ERC20(YVECRV).approve(YCRV, MAX_UINT256)
    ERC20(POOL).approve(YCRV, MAX_UINT256)
    self.legacy_tokens = [YVECRV, YVBOOST]
    self.output_tokens = [YCRV, STYCRV, LPVAULT]

@internal
def lp(_amounts: uint256[2], _min_out: uint256, _recipient: address) -> uint256:
    return Curve(POOL).add_liquidity(_amounts, _min_out)

@external
def zap_from_legacy(_input_token: address, _output_token: address, _amount_in: uint256 = MAX_UINT256, _min_out: uint256 = 0, _recipient: address = msg.sender) -> uint256:
    """
    @notice This function allows users to zap from legacy tokens into yCRV tokens
    @param _input_token The legacy token to migrate from
    @param _output_token The yCRV token to migrate to
    @param _amount_in The yCRV token to migrate to
    @param _min_out The minimum amount of output token to receive
    @param _recipient The address where the output token should be sent
    @return Amount of output token transferred to the _recipient
    """
    assert _input_token in self.legacy_tokens   # dev: invalid input token address
    assert _output_token in self.output_tokens  # dev: invalid output token address
    assert _amount_in > 0

    amount: uint256 = _amount_in
    if amount == MAX_UINT256:
        amount = ERC20(_input_token).balanceOf(msg.sender)

    # Phase 1: Convert starting token to YVECRV
    ycrv_out: uint256 = 0
    assert ERC20(_input_token).transferFrom(msg.sender, self, amount)
    if _input_token == YVECRV:
        ycrv_out = amount
    elif _input_token == YVBOOST:
        ycrv_out = Vault(YVBOOST).withdraw(amount)
    else:
        assert False # Should never reach

    # Phase 2: Burn YVECRV to mint YCRV
    if _output_token == YCRV:
        IYCRV(YCRV).burn_to_mint(ycrv_out, _recipient)
        assert ycrv_out >= _min_out
        return ycrv_out
    IYCRV(YCRV).burn_to_mint(ycrv_out)

    # Phase 3: Convert YCRV to output token
    if _output_token == STYCRV: # ST-YCRV
        amount_out: uint256 = Vault(STYCRV).deposit(ycrv_out, _recipient)
        assert amount_out >= _min_out
        return amount_out
    elif _output_token == LPVAULT: # LP-YCRV
        shares_out: uint256 = Vault(LPVAULT).deposit(self.lp([0, ycrv_out], _min_out, _recipient))
        assert shares_out >=  _min_out
        return shares_out
    assert False # Should never reach
    return 0

@external
def set_admin(_proposed_admin: address):
    assert msg.sender == self.admin
    self.admin = _proposed_admin
    log UpdateAdmin(_proposed_admin)

@external
def sweep(_token: address, _amount: uint256 = MAX_UINT256):
    assert msg.sender == self.admin
    value: uint256 = _amount
    if value == MAX_UINT256:
        value = ERC20(_token).balanceOf(self)
    ERC20(_token).transfer(self.admin, value)

@view
@external
def calc_normalized_out_legacy(_input_token: address, _output_token: address, _amount_in: uint256 = MAX_UINT256) -> uint256:
    """
    @notice This view returns the expected amount of tokens output after conversion assuming no slippage / price impact
    @dev use this value 
    @param _input_token The legacy token to migrate from
    @param _output_token The yCRV token to migrate to
    @param _amount_in The yCRV token to migrate to
    @return Amount of output token transferred to the _recipient
    """
    assert _input_token in self.legacy_tokens   # dev: invalid input token address
    assert _output_token in self.output_tokens  # dev: invalid output token address
    if _amount_in == 0:
        return 0

    amount: uint256 = _amount_in
    if _input_token == YVBOOST:
        amount = Vault(YVBOOST).pricePerShare() * amount / 10 ** 18
    
    if _output_token == YCRV:
        return amount
    elif _output_token == STYCRV:
        return amount * 10 ** 18 / Vault(STYCRV).pricePerShare()
    else:
        assert _output_token == LPVAULT
        return amount * 10 ** 18 / Curve(POOL).get_virtual_price()

@view
@external
def calc_normalized_out(_input_token: address, _output_token: address, _amount_in: uint256 = MAX_UINT256) -> uint256:
    """
    @notice This view returns the expected amount of tokens output after conversion assuming no slippage / price impact
    @dev use this value 
    @param _input_token The legacy token to migrate from
    @param _output_token The yCRV token to migrate to
    @param _amount_in The yCRV token to migrate to
    @return Amount of output token transferred to the _recipient
    """
    assert _input_token in self.output_tokens   # dev: invalid input token address
    assert _output_token in self.output_tokens  # dev: invalid output token address
    if _amount_in == 0:
        return 0
    if _input_token == _output_token:
        return _amount_in

    amount: uint256 = _amount_in
    if _input_token == STYCRV:
        amount = Vault(STYCRV).pricePerShare() * amount / 10 ** 18
    if _input_token == LPVAULT:
        lp_amount: uint256 = Vault(LPVAULT).pricePerShare() * amount / 10 ** 18
        amount = Curve(POOL).get_virtual_price() * amount / 10 ** 18
    if _output_token == YCRV:
        return amount
    elif _output_token == STYCRV:
        return amount * 10 ** 18 / Vault(STYCRV).pricePerShare()
    else:
        assert _output_token == LPVAULT
        return amount * 10 ** 18 / Curve(POOL).get_virtual_price()

@view
@external
def calc_expected_out_legacy(_input_token: address, _output_token: address, _amount_in: uint256 = MAX_UINT256) -> uint256:
    """
    @notice This view returns the expected amount of tokens output after conversion assuming no slippage / price impact
    @dev use this value 
    @param _input_token The legacy token to migrate from
    @param _output_token The yCRV token to migrate to
    @param _amount_in The yCRV token to migrate to
    @return Amount of output token transferred to the _recipient
    """
    assert _input_token in self.legacy_tokens   # dev: invalid input token address
    assert _output_token in self.output_tokens  # dev: invalid output token address
    if _amount_in == 0:
        return 0

    amount: uint256 = _amount_in
    if _input_token == YVBOOST:
        amount = Vault(YVBOOST).pricePerShare() * amount / 10 ** 18
    
    if _output_token == YCRV:
        return amount
    elif _output_token == STYCRV:
        return amount * 10 ** 18 / Vault(STYCRV).pricePerShare()
    else:
        assert _output_token == LPVAULT
        return amount * 10 ** 18 / Curve(POOL).get_virtual_price()
        
@view
@external
def calc_expected_out(_input_token: address, _output_token: address, _amount_in: uint256 = MAX_UINT256) -> uint256:
    """
    @notice This view returns the expected amount of tokens output after conversion assuming no slippage / price impact
    @dev use this value 
    @param _input_token The legacy token to migrate from
    @param _output_token The yCRV token to migrate to
    @param _amount_in The yCRV token to migrate to
    @return Amount of output token transferred to the _recipient
    """
    assert _input_token in self.output_tokens   # dev: invalid input token address
    assert _output_token in self.output_tokens  # dev: invalid output token address
    if _amount_in == 0:
        return 0
    if _input_token == _output_token:
        return _amount_in

    amount: uint256 = _amount_in
    if _input_token == STYCRV:
        amount = Vault(STYCRV).pricePerShare() * amount / 10 ** 18
    if _input_token == LPVAULT:
        lp_amount: uint256 = Vault(LPVAULT).pricePerShare() * amount / 10 ** 18
        amount = Curve(POOL).calc_token_amount([0, lp_amount], False) # Withdraw = False
    else:
        assert _input_token == YCRV

    if _output_token == YCRV:
        return amount
    elif _output_token == STYCRV:
        return amount * 10 ** 18 / Vault(STYCRV).pricePerShare()
    else:
        assert _output_token == LPVAULT
        lp_amount: uint256 = Vault(LPVAULT).pricePerShare() * amount / 10 ** 18
        return Curve(POOL).calc_token_amount([0,lp_amount], True) # Deposit = True