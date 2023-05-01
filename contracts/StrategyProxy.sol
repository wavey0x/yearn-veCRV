// SPDX-License-Identifier: MIT

pragma solidity ^0.8.15;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import "../interfaces/yearn/IProxy.sol";
import "../interfaces/curve/Mintr.sol";
import "../interfaces/curve/Gauge.sol";

library SafeProxy {
    function safeExecute(
        IProxy proxy,
        address to,
        uint256 value,
        bytes memory data
    ) internal {
        (bool success, ) = proxy.execute(to, value, data);
        require(success);
    }
}

interface VeBAL {
    function locked__end(address user) external returns (uint);
}

interface IPool {
    function getPoolId() external view returns (bytes32);
}

interface IGaugeController {
    function gauge_types(address _gauge) external view returns (int128);
}

interface FeeDistribution {
    function claimToken(address user, IERC20 token)
        external
        returns (uint256);
    
    function getUserTimeCursor(address user) external view returns (uint256);
}

contract StrategyProxy {
    using SafeERC20 for IERC20;
    // using Address for address;
    using SafeProxy for IProxy;

    uint256 private constant WEEK = 604800; // Number of seconds in a week

    /// @notice Yearn's voter proxy. Typically referred to as "voter".
    IProxy public constant proxy = IProxy(0xBA11E7024cbEB1dd2B401C70A83E0d964144686C);

    /// @notice Balancer's token minter.
    address public constant mintr = 0x239e55F427D44C3cc793f49bFB507ebe76638a2b;

    /// @notice Balancer's BAL token address.
    address public constant bal = 0xba100000625a3754423978a60c9317c58a424e3D;

    /// @notice Curve's BAL/WETH token address.
    address public constant balweth = 0x5c6Ee304399DBdB9C8Ef030aB642B10820DB8F56;

    /// @notice Recipient of weekly bb-a-USD admin fees. Default of st-yBAL strategy address.
    address public feeRecipient = 0x93A62dA5a14C80f265DAbC077fCEE437B1a0Efde; // incorrect - st-yBAL strat yet to be deployed

    /// @notice Balancer's fee distributor contract.
    FeeDistribution public constant feeDistribution = FeeDistribution(0xD3cf852898b21fc233251427c2DC93d3d604F3BB);

    /// @notice Balancer's vote-escrowed BAL address.
    VeBAL public constant veBAL  = VeBAL(0xC128a9954e6c874eA3d62ce62B468bA073093F25);

    /// @notice Balancer's gauge controller.
    IGaugeController public constant gaugeController = IGaugeController(0xC128468b7Ce63eA702C1f104D55A2566b13D3ABD);

    /// @notice The token Balancer pays fees in.
    address public feeToken = 0xA13a9247ea42D743238089903570127DdA72fE44;

    /// @notice Look up the strategy approved for a given Balancer gauge.
    mapping(address => address) public strategies;

    /// @notice Check if a gauge reward token is approved for claiming.
    mapping(address => bool) public rewardTokenApproved;

    /// @notice Look up the recipient approved for a given extra token (typically from bribes).
    mapping(address => address) public extraTokenRecipient;

    /// @notice Check if an address is an approved voter for gauge weights.
    mapping(address => bool) public voters;

    /// @notice Check if an address is an approved locker of BALWETH tokens.
    mapping(address => bool) public lockers;

    /// @notice Current governance address.
    address public governance = 0x36666EC6315E9606f03fc6527E396B95bcA4D384;

    /// @notice Curve vault factory address. 
    address public factory;

    /// @notice This voter's last time cursor, updated on each claim of admin fees.
    uint256 public lastTimeCursor;

    // Events so that indexers can keep track of key actions
    event GovernanceSet(address indexed governance);
    event FeeRecipientSet(address indexed feeRecipient);
    event StrategyApproved(address indexed gauge, address indexed strategy);
    event StrategyRevoked(address indexed gauge, address indexed strategy);
    event VoterApproved(address indexed voter);
    event VoterRevoked(address indexed voter);
    event LockerApproved(address indexed locker);
    event LockerRevoked(address indexed locker);
    event BalFeesClaimed(address indexed recipient, uint256 amount);
    event AdminFeesClaimed(address indexed recipient, uint256 amount);
    event ExtraTokenRecipientApproved(address indexed token, address indexed recipient);
    event ExtraTokenRecipientRevoked(address indexed token, address indexed recipient);
    event RewardTokenApproved(address indexed token, bool approved);
    event FactorySet(address indexed factory);
    event TokenClaimed(address indexed token, address indexed recipient, uint balance);
    event FeeTokenSet(address indexed feeToken);

    /// @notice Set Balancer vault factory address.
    /// @dev Must be called by governance.
    /// @param _factory Address to set as balancer vault factory.
    function setFactory(address _factory) external {
        require(msg.sender == governance, "!governance");
        require(_factory != factory, "already set");
        factory = _factory;
        emit FactorySet(_factory);
    }
    
    /// @notice Set governance address.
    /// @dev Must be called by current governance.
    /// @param _governance Address to set as governance.
    function setGovernance(address _governance) external {
        require(msg.sender == governance, "!governance");
        require(_governance != governance, "already set");
        governance = _governance;
        emit GovernanceSet(_governance);
    }

    /// @notice Set recipient of weekly bb-a-USD admin fees and bal rewards.
    /// @dev Only a single address can be approved at any time.
    ///  Must be called by governance.
    /// @param _feeRecipient Address to approve for fees.
    function setFeeRecipient(address _feeRecipient) external {
        require(msg.sender == governance, "!governance");
        require(_feeRecipient != address(0), "!zeroaddress");
        require(_feeRecipient != feeRecipient, "already set");
        feeRecipient = _feeRecipient;
        emit FeeRecipientSet(_feeRecipient);
    }

    /// @notice Add strategy to a gauge.
    /// @dev Must be called by governance or factory.
    /// @param _gauge Gauge to permit strategy on.
    /// @param _strategy Strategy to approve on gauge.
    function approveStrategy(address _gauge, address _strategy) external {
        require(msg.sender == governance || msg.sender == factory, "!access");
        require(_strategy != address(0), "disallow zero");
        require(strategies[_gauge] != _strategy, "already approved");
        strategies[_gauge] = _strategy;
        emit StrategyApproved(_gauge, _strategy);
    }

    /// @notice Clear any previously approved strategy to a gauge.
    /// @dev Must be called by governance.
    /// @param _gauge Gauge from which to remove strategy.
    function revokeStrategy(address _gauge) external {
        require(msg.sender == governance, "!governance");
        address _strategy = strategies[_gauge];
        require(_strategy != address(0), "already revoked");
        strategies[_gauge] = address(0);
        emit StrategyRevoked(_gauge, _strategy);
    }

    /// @notice Use to approve a recipient. Recipients have privileges to claim tokens directly from the voter.
    /// @dev For safety: Recipients cannot be added for LP tokens or gauge tokens (approved via gauge controller).
    ///  Must be called by governance.
    /// @param _token Token to permit a recipient for.
    /// @param _recipient Recipient to approve for token.
    function approveExtraTokenRecipient(address _token, address _recipient) external {
        require(msg.sender == governance, "!governance");
        require(_recipient != address(0), "disallow zero");
        require(extraTokenRecipient[_token] != _recipient, "already approved");
        require(_isSafeToken(_token), "!safeToken");
        extraTokenRecipient[_token] = _recipient;
        emit ExtraTokenRecipientApproved(_token, _recipient);
    }

    /// @notice Clear any previously approved token recipient.
    /// @dev Must be called by governance.
    /// @param _token Token from which to clearn recipient.
    function revokeExtraTokenRecipient(address _token) external {
        require(msg.sender == governance, "!governance");
        address recipient = extraTokenRecipient[_token];
        require(recipient != address(0), "already revoked");
        extraTokenRecipient[_token] = address(0);
        emit ExtraTokenRecipientRevoked(_token, recipient);
    }

    /// @notice Claim extra tokens sitting in the voter.
    /// @dev Must be called by an approved recipient. See approveExtraTokenRecipient()
    ///  for more info.
    /// @param _token Token to claim.
    function claimExtraToken(address _token) external {
        address recipient = extraTokenRecipient[_token];
        require(msg.sender == recipient);
        uint256 _balance = IERC20(_token).balanceOf(address(proxy));
        if (_balance > 0) {
            proxy.safeExecute(_token, 0, abi.encodeWithSignature("transfer(address,uint256)", recipient, _balance));
            emit TokenClaimed(_token, recipient, _balance);
        }
    }

    /// @notice Approve an address for voting on gauge weights.
    /// @dev Must be called by governance.
    /// @param _voter Voter to add.
    function approveVoter(address _voter) external {
        require(msg.sender == governance, "!governance");
        require(!voters[_voter], "already approved");
        voters[_voter] = true;
        emit VoterApproved(_voter);
    }

    /// @notice Remove ability to vote on gauge weights.
    /// @dev Must be called by governance.
    /// @param _voter Voter to remove.
    function revokeVoter(address _voter) external {
        require(msg.sender == governance, "!governance");
        require(voters[_voter], "already revoked");
        voters[_voter] = false;
        emit VoterRevoked(_voter);
    }

    /// @notice Approve an address for locking BALWETH.
    /// @dev Must be called by governance.
    /// @param _locker Locker to add.
    function approveLocker(address _locker) external {
        require(msg.sender == governance, "!governance");
        require(!lockers[_locker], "already approved");
        lockers[_locker] = true;
        emit LockerApproved(_locker);
    }

    /// @notice Remove ability to max lock BALWETH.
    /// @dev Must be called by governance.
    /// @param _locker Locker to remove.
    function revokeLocker(address _locker) external {
        require(msg.sender == governance, "!governance");
        require(lockers[_locker], "already revoked");
        lockers[_locker] = false;
        emit LockerRevoked(_locker);
    }

    /// @notice Lock BALWETH into veBAL contract.
    /// @dev Must be called by governance or locker.
    function lock() external {
        require(msg.sender == governance || lockers[msg.sender], "!locker");
        uint256 amount = IERC20(balweth).balanceOf(address(proxy));
        if (amount > 0) proxy.increaseAmount(amount);
    }

    /// @notice Extend veBAL lock time to maximum amount of 1 year.
    /// @dev Must be called by governance or locker.
    function maxLock() external {
        require(msg.sender == governance || lockers[msg.sender], "!locker");
        uint max = block.timestamp + (365 days);
        uint lock_end = veBAL.locked__end(address(proxy));
        if(lock_end < (max / WEEK) * WEEK){
            proxy.safeExecute(
                address(veBAL), 
                0, 
                abi.encodeWithSignature("increase_unlock_time(uint256)", max)
            );
        }
    }

    /// @notice Vote on a gauge.
    /// @dev Must be called by governance or voter.
    /// @param _gauge The gauge to vote on.
    /// @param _weight Weight to vote with.
    function vote(address _gauge, uint256 _weight) external {
        require(msg.sender == governance || voters[msg.sender], "!voter");
        _vote(_gauge, _weight);
    }

    /// @notice Vote on multiple gauges.
    /// @dev Must be called by governance or voter.
    /// @param _gauges List of gauges to vote on.
    /// @param _weights List of weight to vote with.
    function vote_many(address[] calldata _gauges, uint256[] calldata _weights) external {
        require(msg.sender == governance || voters[msg.sender], "!voter");
        require(_gauges.length == _weights.length, "!mismatch");
        for(uint256 i = 0; i < _gauges.length; i++) {
            _vote(_gauges[i], _weights[i]);
        }
    }

    function _vote(address _gauge, uint256 _weight) internal {
        proxy.safeExecute(address(gaugeController), 0, abi.encodeWithSignature("vote_for_gauge_weights(address,uint256)", _gauge, _weight));
    }

    /// @notice Withdraw exact amount of LPs from gauge.
    /// @dev Must be called by the strategy approved for the given gauge.
    /// @param _gauge The gauge from which to withdraw.
    /// @param _token The LP token to withdraw from gauge.
    /// @param _amount The exact amount of LPs with withdraw.
    function withdraw(
        address _gauge,
        address _token,
        uint256 _amount
    ) public returns (uint256) {
        require(strategies[_gauge] == msg.sender, "!strategy");
        uint256 _balance = IERC20(_token).balanceOf(address(proxy));
        proxy.safeExecute(_gauge, 0, abi.encodeWithSignature("withdraw(uint256)", _amount));
        _balance = IERC20(_token).balanceOf(address(proxy)) - _balance;
        proxy.safeExecute(_token, 0, abi.encodeWithSignature("transfer(address,uint256)", msg.sender, _balance));
        return _balance;
    }

    /// @notice Find Yearn voter's full balance within a given gauge.
    /// @param _gauge The gauge from which to check balance.
    function balanceOf(address _gauge) public view returns (uint256) {
        return IERC20(_gauge).balanceOf(address(proxy));
    }

    /// @notice Withdraw full balance of voter's LPs from gauge.
    /// @param _gauge The gauge from which to withdraw.
    /// @param _token The LP token to withdraw from gauge.
    function withdrawAll(address _gauge, address _token) external returns (uint256) {
        return withdraw(_gauge, _token, balanceOf(_gauge));
    }

    /// @notice Takes care of depositing BPTs into gauge.
    /// @dev Strategy must first transfer LPs to this contract prior to calling.
    ///  Must be called by strategy approved for this gauge.
    /// @param _gauge The gauge to deposit LP token into.
    /// @param _token The LP token to deposit into gauge.
    function deposit(address _gauge, address _token) external {
        require(strategies[_gauge] == msg.sender, "!strategy");
        uint256 _balance = IERC20(_token).balanceOf(address(this));
        IERC20(_token).safeTransfer(address(proxy), _balance);
        _balance = IERC20(_token).balanceOf(address(proxy));

        proxy.safeExecute(_token, 0, abi.encodeWithSignature("approve(address,uint256)", _gauge, 0));
        proxy.safeExecute(_token, 0, abi.encodeWithSignature("approve(address,uint256)", _gauge, _balance));
        proxy.safeExecute(_gauge, 0, abi.encodeWithSignature("deposit(uint256)", _balance));
    }

    /// @notice Abstracts the BAL minting and transfers to an approved strategy with BAL earnings.
    /// @dev Designed to be called within the harvest function of a strategy.
    /// @param _gauge The gauge which this strategy is claiming BAL from.
    function harvest(address _gauge) external {
        require(strategies[_gauge] == msg.sender, "!strategy");
        uint256 _balance = IERC20(bal).balanceOf(address(proxy));
        proxy.safeExecute(mintr, 0, abi.encodeWithSignature("mint(address)", _gauge));
        _balance = IERC20(bal).balanceOf(address(proxy)) - _balance;
        proxy.safeExecute(bal, 0, abi.encodeWithSignature("transfer(address,uint256)", msg.sender, _balance));
    }

    /// @notice Claim BAL and our share of weekly admin fees from Balancer fee distributor.
    /// @dev Admin fees become available every Thursday, so we run this expensive
    ///  logic only once per week. May only be called by feeRecipient.
    /// @param _recipient The address to which we transfer BAL and bb-a-USD.
    function claim(address _recipient) external {
        require(msg.sender == feeRecipient, "!approved");
        if (!claimable()) return;

        feeDistribution.claimToken(address(proxy), IERC20(bal));
        feeDistribution.claimToken(address(proxy), IERC20(feeToken));
        
        lastTimeCursor = feeDistribution.getUserTimeCursor(address(proxy));

        uint amount = IERC20(bal).balanceOf(address(proxy));
        if (amount > 0) {
            proxy.safeExecute(bal, 0, abi.encodeWithSignature("transfer(address,uint256)", _recipient, amount));
            emit BalFeesClaimed(_recipient, amount);
        }

        amount = IERC20(feeToken).balanceOf(address(proxy));
        if (amount > 0) {
            proxy.safeExecute(feeToken, 0, abi.encodeWithSignature("transfer(address,uint256)", _recipient, amount));
            emit AdminFeesClaimed(_recipient, amount);
        }
    }

    /// @notice Check if we are in a new rewards period
    function claimable() public view returns (bool) {
        /// @dev add 1 day to allow the give the burner mechanism a buffer
        if (block.timestamp < lastTimeCursor + 1 days) return false;
        return true;
    }

    /// @notice Claim non-BAL token incentives from the gauge and transfer to strategy.
    /// @dev Reward tokens must first be approved via approveRewardToken() before claiming.
    ///  Must be called by the strategy approved for the given gauge.
    /// @param _gauge The gauge which this strategy is claiming rewards.
    /// @param _token The token to be claimed to the approved strategy.
    function claimRewards(address _gauge, address _token) external {
        require(strategies[_gauge] == msg.sender, "!strategy");
        require(rewardTokenApproved[_token], "!approvedToken");
        Gauge(_gauge).claim_rewards(address(proxy));
        _transferBalance(_token);
    }

    /// @notice Claim non-BAL token incentives from the gauge and transfer to strategy.
    /// @dev Must be called by the strategy approved for the given gauge.
    /// @param _gauge The gauge which this strategy is claiming rewards.
    /// @param _tokens The token(s) to be claimed to the approved strategy.
    function claimManyRewards(address _gauge, address[] memory _tokens) external {
        require(strategies[_gauge] == msg.sender, "!strategy");
        Gauge(_gauge).claim_rewards(address(proxy));
        for (uint256 i; i < _tokens.length; ++i) {
            require(rewardTokenApproved[_tokens[i]], "!approvedToken");
            _transferBalance(_tokens[i]);
        }
    }

    /// @notice Approve reward tokens to be claimed by strategies.
    /// @dev Must be called by governance.
    /// @param _token The token to be claimed.
    function approveRewardToken(address _token) external {
        require(msg.sender == governance, "!governance");
        require(_isSafeToken(_token),"!safeToken");
        require(!rewardTokenApproved[_token]);
        rewardTokenApproved[_token] = true;
        emit RewardTokenApproved(_token, true);
    }

    /// @notice Revoke approval of reward tokens to be claimed by strategies.
    /// @dev Must be called by governance.
    /// @param _token The token to be revoked.
    function revokeRewardToken(address _token) external {
        require(msg.sender == governance, "!governance");
        require(rewardTokenApproved[_token]);
        rewardTokenApproved[_token] = false;
        emit RewardTokenApproved(_token, false);
    }

    /// @notice Set a new fee token in the event Balancer governance makes a change.
    /// @param _token New fee token.
    function setFeeToken(address _token) external {
        require(msg.sender == governance, "!governance");
        require(feeToken != _token);
        feeToken = _token;
        emit FeeTokenSet(_token);
    }

    // make sure a strategy can't yoink gauge or LP tokens.
    function _isSafeToken(address _token) internal returns (bool) {
        if (_token == bal) return false; /// @dev: balweth and bbausd are covered as lp tokens
        try gaugeController.gauge_types(_token) {
            return false;
        }
        catch {} /// @dev: Since we expect try should fail, proceed without any catch logic error here.
        try IPool(_token).getPoolId() {
            return false;
        }
        catch {} /// @dev: Since we expect try should fail, proceed without any catch logic error here.
        return true;
    }

    function _transferBalance(address _token) internal {
        proxy.safeExecute(_token, 0, abi.encodeWithSignature("transfer(address,uint256)", msg.sender, IERC20(_token).balanceOf(address(proxy))));
    }
}