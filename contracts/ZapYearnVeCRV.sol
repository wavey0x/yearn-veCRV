
// SPDX-License-Identifier: MIT
pragma solidity ^0.6.12;

import {
    SafeERC20,
    SafeMath,
    IERC20,
    Address
} from "@openzeppelinV3/contracts/token/ERC20/SafeERC20.sol";
/*
    This zap performs each of the following 3 conversions
    1) CRV -> LP -> vault deposit
    2) CRV -> yvBOOST
    3) yvBOOST -> LP -> vault deposit
*/

interface ICurve {
    function exchange(int128 i, int128 j, uint256 dx, uint256 _min_dy) external view returns (uint256);
    function add_liquidity(uint256[] calldata amounts, uint256 _min_mint_amount) external view returns (uint256);
}

interface IVault {
    function withdraw(uint256 amount) external view returns (uint256);
    function deposit(uint256 amount, address receiver) external view returns (uint256);
}

contract ZapYearnVeCRV {
    using SafeMath for uint256;
    using SafeERC20 for IERC20;

    address public gov = 0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52;
    IERC20 public CRV = IERC20(0xD533a949740bb3306d119CC777fa900bA034cd52);
    IERC20 public yveCRV = IERC20(0xc5bDdf9843308380375a611c18B50Fb9341f502A);
    IVault public yvBOOST = IVault(0x9d409a0A012CFbA9B15F6D4B36Ac57A46966Ab9a);
    IVault public yvCrvYveCRV = IVault(0x2E919d27D515868f3D5Bc9110fa738f9449FC6ad);
    ICurve public pool = ICurve(0x7E46fd8a30869aa9ed55af031067Df666EfE87da);  

    constructor() public {
        CRV.approve(address(pool), type(uint256).max);
        yveCRV.approve(address(pool), type(uint256).max);
        yveCRV.approve(address(yvBOOST), type(uint256).max);
        IERC20(address(pool)).approve(address(yvCrvYveCRV), type(uint256).max);
    }

    /// @notice Convert CRV to yvBOOST by trading to yveCRV and depositing
    /// @dev We can assume it is always optimal to swap to yveCRV since the peg should never exceed 1:1 due to arbers minting
    /// @param _amount Amount of CRV to convert
    /// @param _minOut Minimum yveCRV out from the CRV --> yveCRV swap
    /// @return uint256 Amount of yvBOOST received
    function zapCRVtoYvBOOST(uint256 _amount, uint256 _minOut, address _recipient) external returns(uint256) {
        CRV.transferFrom(msg.sender, address(this), _amount);
        uint256 amountYveCRV = pool.exchange(0, 1, _amount, _minOut);
        return yvBOOST.deposit(amountYveCRV, _recipient);
    }

    /// @notice Convert CRV to LPs and deposit into Yearn vault to compound
    /// @dev We can assume it is always optimal to swap to yveCRV since the peg should never exceed 1:1 due to arbers minting
    /// @dev calculate your _minOut by using: amount / pool.virtual_price() - (amount / pool.virtual_price() * slippage_tolerance)
    /// @param _amount Amount of CRV to convert
    /// @param _minOut Minimum acceptable amount of LP tokens to mint from the deposit
    /// @return uint256 Amount of yvTokens received
    function zapCRVtoLPVault(uint256 _amount, uint256 _minOut, address _recipient) external returns(uint256) {
        CRV.transferFrom(msg.sender, address(this), _amount);
        uint256[] memory amounts = new uint256[](2);
        amounts[0] = _amount;
        uint256 lpAmount = lp(amounts, _minOut);
        return yvCrvYveCRV.deposit(lpAmount, _recipient);
    }

    /// @notice Convert yvBOOST to LP and deposit to vault
    /// @dev calculate your _minOut by using: amount / pool.virtual_price() - (amount / pool.virtual_price() * slippage_tolerance)
    /// @param _amount Amount of yvBOOST to convert
    /// @param _minOut Minimum acceptable amount of LP tokens to mint from the deposit
    /// @return uint256 Amount of yvTokens received
    function zapYvBOOSTtoLPVault(uint256 _amount, uint256 _minOut, address _recipient) external returns(uint256) {
        IERC20(address(yvBOOST)).transferFrom(msg.sender, address(this), _amount);
        uint256 yveCRVBalance = yvBOOST.withdraw(_amount);
        uint256[] memory amounts = new uint256[](2);
        amounts[1] = _amount;
        uint256 lpAmount = lp(amounts, _minOut);
        return yvCrvYveCRV.deposit(lpAmount, _recipient);
    }

    /// @notice Perform single-sided LP from either CRV or yveCRV
    /// @param _amounts Amount of yvBOOST to convert
    /// @param _minOut Minimum acceptable amount of LP tokens to mint from the deposit
    /// @return uint256 Amount of LPs minted
    function lp(uint256[] memory _amounts, uint256 _minOut) internal returns(uint256) {
        return pool.add_liquidity(_amounts, _minOut);
    }

    function sweep(IERC20 _token) external returns (uint256 balance){
        balance = _token.balanceOf(address(this));
        if (balance > 0) {
            _token.safeTransfer(gov, balance);
        }   
    }
}