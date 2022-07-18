# @version 0.3.3

from vyper.interfaces import ERC20
from vyper.interfaces import ERC20Detailed

implements: ERC20
implements: ERC20Detailed

event Transfer:
    sender: indexed(address)
    receiver: indexed(address)
    value: uint256

event Approval:
    owner: indexed(address)
    spender: indexed(address)
    value: uint256

event UpdateAdmin:
    admin: indexed(address)

YVECRV: constant(address) = 0xc5bDdf9843308380375a611c18B50Fb9341f502A
name: public(String[32])
symbol: public(String[32])
decimals: public(uint8)

balanceOf: public(HashMap[address, uint256])
allowance: public(HashMap[address, HashMap[address, uint256]])
totalSupply: public(uint256)
burned: public(uint256)
admin: public(address)


@external
def __init__(_name: String[32], _symbol: String[32], _decimals: uint8, _supply: uint256):
    init_supply: uint256 = _supply * 10 ** convert(_decimals, uint256)
    self.name = _name
    self.symbol = _symbol
    self.decimals = _decimals
    self.admin = 0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52

@external
def transfer(_to : address, _value : uint256) -> bool:
    """
    @dev Transfer token for a specified address
    @param _to The address to transfer to.
    @param _value The amount to be transferred.
    """
    self.balanceOf[msg.sender] -= _value
    self.balanceOf[_to] += _value
    log Transfer(msg.sender, _to, _value)
    return True


@external
def transferFrom(_from : address, _to : address, _value : uint256) -> bool:
    """
     @dev Transfer tokens from one address to another.
     @param _from address The address which you want to send tokens from
     @param _to address The address which you want to transfer to
     @param _value uint256 the amount of tokens to be transferred
    """
    self.balanceOf[_from] -= _value
    self.balanceOf[_to] += _value
    self.allowance[_from][msg.sender] -= _value
    log Transfer(_from, _to, _value)
    return True


@external
def approve(_spender : address, _value : uint256) -> bool:
    """
    @dev Approve the passed address to spend the specified amount of tokens on behalf of msg.sender.
    @param _spender The address which will spend the funds.
    @param _value The amount of tokens to be spent.
    """
    self.allowance[msg.sender][_spender] = _value
    log Approval(msg.sender, _spender, _value)
    return True

@internal
def _mint(_to: address, _value: uint256):
    self.totalSupply += _value
    self.balanceOf[_to] += _value
    log Transfer(ZERO_ADDRESS, _to, _value)

@external
def burn_to_mint(_amount: uint256 = MAX_UINT256, _recipient: address = msg.sender):
    """
    @dev burn an amount of yveCRV token and mint yCRV token 1 to 1.
    @param _amount The amount of yveCRV to burn and yCRV to mint.
    @param _recipient The address which minted tokens should be received at.
    """
    assert _recipient not in [self, ZERO_ADDRESS]
    assert _amount > 0
    amount: uint256 = _amount
    if amount == MAX_UINT256:
        amount = ERC20(YVECRV).balanceOf(msg.sender)
    assert ERC20(YVECRV).transferFrom(msg.sender, self, amount)  # dev: no allowance
    self.burned += amount
    self._mint(_recipient, amount)

@external
def set_admin(proposed_admin: address):
    assert msg.sender == self.admin
    self.admin = proposed_admin

    log UpdateAdmin(proposed_admin)

@external
def sweep(token: address, amount: uint256 = MAX_UINT256):
    assert msg.sender == self.admin
    assert token != YVECRV
    value: uint256 = amount
    if value == MAX_UINT256:
        value = ERC20(token).balanceOf(self)
    
    assert ERC20(token).transfer(self.admin, value)

@external
def sweep_yvecrv():
    assert msg.sender == self.admin
    excess: uint256 = ERC20(YVECRV).balanceOf(self) - self.burned
    assert excess > 0
    ERC20(YVECRV).transfer(self.admin, excess)