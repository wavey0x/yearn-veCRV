// SPDX-License-Identifier: MIT

pragma solidity ^0.8.15;

// These are the core Yearn libraries
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/math/Math.sol";

import "@yearnvaults/contracts/BaseStrategy.sol";

interface VoteEscrow {
    function create_lock(uint, uint) external;
    function increase_amount(uint) external;
    function withdraw() external;
}

contract BalancerYBALVoter {
    using SafeERC20 for IERC20;
    address public escrow; // veContract addr
    address public token;
    address public governance;
    address public strategy; // StrategyProxy
    string public name;

    bool isInitialized = false;
    
    constructor() public {
        governance = msg.sender;
    }

    function initialize(
        address _veContract,
        address _tokenToLock,
        string _name

    ) public {
        require(!isInitialized, "Contract is already initialized");
        require(msg.sender == governance, "!governance");

        escrow = _veContract;
        token = _tokenToLock;
        name = _name;

        isInitialized = true;
    }
    
    function getName() external pure returns (string memory) {
        return name;
    }

    function createLock(uint _value, uint _unlockTime) external {
        require(msg.sender == strategy || msg.sender == governance, "!authorized");
        IERC20(balweth).safeApprove(escrow, 0);
        IERC20(balweth).safeApprove(escrow, _value);
        VoteEscrow(escrow).create_lock(_value, _unlockTime);
    }
    
    function increaseAmount(uint _value) external {
        require(msg.sender == strategy || msg.sender == governance, "!authorized");
        IERC20(balweth).safeApprove(escrow, 0);
        IERC20(balweth).safeApprove(escrow, _value);
        VoteEscrow(escrow).increase_amount(_value);
    }
    
    function release() external {
        require(msg.sender == strategy || msg.sender == governance, "!authorized");
        VoteEscrow(escrow).withdraw();
    }
    
    function setStrategy(address _strategy) external {
        require(msg.sender == governance, "!governance");
        strategy = _strategy;
    }

    function setGovernance(address _governance) external {
        require(msg.sender == governance, "!governance");
        governance = _governance;
    }
    
    function execute(address to, uint value, bytes calldata data) external returns (bool, bytes memory) {
        require(msg.sender == strategy || msg.sender == governance, "!governance");
        (bool success, bytes memory result) = to.call{value:value}(data);
        
        return (success, result);
    }
}