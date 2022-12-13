// SPDX-License-Identifier: MIT

pragma solidity ^0.6.12;

import "@openzeppelinV3/contracts/token/ERC20/IERC20.sol";
import "@openzeppelinV3/contracts/math/SafeMath.sol";
import "@openzeppelinV3/contracts/utils/Address.sol";
import "@openzeppelinV3/contracts/token/ERC20/SafeERC20.sol";

import "../interfaces/yearn/IProxy.sol";
import "../interfaces/curve/Mintr.sol";
import "../interfaces/curve/FeeDistribution.sol";
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

interface VeCRV {
    function increase_unlock_time(uint256 _time) external;
    function locked__end(address user) external returns (uint);
}

interface IMetaRegistry {
    function get_pool_from_lp_token(address _lp) external view returns (address);
}

interface IGaugeController {
    function gauge_types(address _gauge) external view returns (int128);
}

contract StrategyProxy {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;
    using SafeProxy for IProxy;

    uint256 private constant WEEK = 604800; // Number of seconds in a week
    IProxy public constant proxy = IProxy(0xF147b8125d2ef93FB6965Db97D6746952a133934); // Refer to this as "voter" contract
    address public constant mintr = address(0xd061D61a4d941c39E5453435B6345Dc261C2fcE0);
    address public constant crv = address(0xD533a949740bb3306d119CC777fa900bA034cd52);
    address public constant gauge = address(0x2F50D538606Fa9EDD2B11E2446BEb18C9D5846bB);
    address public constant yveCRV = address(0xc5bDdf9843308380375a611c18B50Fb9341f502A);
    address public constant CRV3 = address(0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490);
    address public feeRecipient = address(0xc5bDdf9843308380375a611c18B50Fb9341f502A); // Default value is yveCRV
    FeeDistribution public constant feeDistribution = FeeDistribution(0xA464e6DCda8AC41e03616F95f4BC98a13b8922Dc);
    VeCRV public constant veCRV  = VeCRV(0x5f3b5DfEb7B28CDbD7FAba78963EE202a494e2A2);
    IMetaRegistry public constant metaRegistry = IMetaRegistry(0xF98B45FA17DE75FB1aD0e7aFD971b0ca00e379fC);
    IGaugeController public constant gaugeController = IGaugeController(0x2F50D538606Fa9EDD2B11E2446BEb18C9D5846bB);
    
    mapping(address => address) public strategies;
    mapping(address => address) public tokenRecipient;
    mapping(address => bool) public voters;
    mapping(address => bool) public lockers;
    address public governance;
    address public factory;
    uint256 public lastTimeCursor;

    // Events so that indexers can keep track of key actions
    event GovernanceSet(address governance);
    event FeeRecipientSet(address feeRecipient);
    event StrategyApproved(address gauge, address strategy);
    event StrategyRevoked(address gauge, address strategy);
    event VoterApproved(address voter);
    event VoterRevoked(address voter);
    event LockerApproved(address locker);
    event LockerRevoked(address locker);
    event AdminFeesClaimed(address recipient, uint256 amount);
    event TokenRecipientApproved(address token, address recipient);
    event TokenRecipientRevoked(address token, address recipient);
    event FactorySet(address factory);
    event TokenClaimed(address token, address recipient, uint balance);

    constructor() public {
        governance = msg.sender;
    }

    /// @notice Set curve vault factory address
    /// @param _factory Address to set as curve vault factory
    function setFactory(address _factory) external {
        require(msg.sender == governance, "!governance");
        require(_factory != factory, "already set");
        factory = _factory;
        emit FactorySet(_factory);
    }
    
    /// @notice Set governance address
    /// @param _governance Address to set as governance
    function setGovernance(address _governance) external {
        require(msg.sender == governance, "!governance");
        require(_governance != governance, "already set");
        governance = _governance;
        emit GovernanceSet(_governance);
    }

    /// @notice Set recipient of weekly 3CRV admin fees
    /// @dev Only a single address can be approved at any time
    /// @param _feeRecipient Address to approve for fees
    function setFeeRecipient(address _feeRecipient) external {
        require(msg.sender == governance, "!governance");
        require(_feeRecipient != address(0), "!zeroaddress");
        require(_feeRecipient != feeRecipient, "already set");
        feeRecipient = _feeRecipient;
        emit FeeRecipientSet(_feeRecipient);
    }

    /// @notice Add strategy to a gauge
    /// @param _gauge Gauge to permit strategy on
    /// @param _strategy Strategy to approve on gauge
    function approveStrategy(address _gauge, address _strategy) external {
        require(msg.sender == governance || msg.sender == factory, "!access");
        require(_strategy != address(0), "disallow zero");
        require(strategies[_gauge] != _strategy, "already approved");
        strategies[_gauge] = _strategy;
        emit StrategyApproved(_gauge, _strategy);
    }

    /// @notice Clear any previously approved strategy to a gauge
    /// @param _gauge Gauge from which to remove strategy
    function revokeStrategy(address _gauge) external {
        require(msg.sender == governance, "!governance");
        address _strategy = strategies[_gauge];
        require(_strategy != address(0), "already revoked");
        strategies[_gauge] = address(0);
        emit StrategyRevoked(_gauge, _strategy);
    }

    /// @notice Use to approve a recipient. Recipients have privileges to claim tokens directly from the voter.
    /// @dev For safety: Recipients cannot be added for LP tokens or gauge tokens (approved via gauge controller).
    /// @param _token Token to permit a recpient for
    /// @param _recipient Recpient to approve for token
    function approveTokenRecipient(address _token, address _recipient) external {
        require(msg.sender == governance, "!governance");
        require(_recipient != address(0), "disallow zero");
        require(tokenRecipient[_token] != _recipient, "already approved");
        require(_token != crv, "disallow CRV");
        try gaugeController.gauge_types(_token) {
            revert('Gauge tokens cannot be approved');
        }
        catch {
            // @dev: Since we expect try should fail, proceed without any catch logic error here.
        }
        address pool = metaRegistry.get_pool_from_lp_token(_token);
        require(pool == address(0), "disallow LPs");
        tokenRecipient[_token] = _recipient;
        emit TokenRecipientApproved(_token, _recipient);
    }

    /// @notice Clear any previously approved token recipient
    /// @param _token Token from which to clearn recipient
    function revokeTokenRecipient(address _token) external {
        require(msg.sender == governance, "!governance");
        address recipient = tokenRecipient[_token];
        require(recipient != address(0), "already revoked");
        tokenRecipient[_token] = address(0);
        emit TokenRecipientRevoked(_token, recipient);
    }

    /// @notice Approve an address for voting on gauge weights
    /// @param _voter Voter to add
    function approveVoter(address _voter) external {
        require(msg.sender == governance, "!governance");
        require(!voters[_voter], "already approved");
        voters[_voter] = true;
        emit VoterApproved(_voter);
    }

    /// @notice Remove ability to vote on gauge weights
    /// @param _voter Voter to remove
    function revokeVoter(address _voter) external {
        require(msg.sender == governance, "!governance");
        require(voters[_voter], "already revoked");
        voters[_voter] = false;
        emit VoterRevoked(_voter);
    }

    /// @notice Approve an address for voting on gauge weights
    /// @param _locker Voter to add
    function approveLocker(address _locker) external {
        require(msg.sender == governance, "!governance");
        require(!lockers[_locker], "already approved");
        lockers[_locker] = true;
        emit LockerApproved(_locker);
    }

    /// @notice Remove ability to max lock CRV
    /// @param _locker Locker to remove
    function revokeLocker(address _locker) external {
        require(msg.sender == governance, "!governance");
        require(lockers[_locker], "already revoked");
        lockers[_locker] = false;
        emit LockerRevoked(_locker);
    }

    /// @notice Lock CRV into veCRV contract
    /// @dev Permissionless, anyone is encouraged to call it when CRV is available to lock
    function lock() external {
        uint256 amount = IERC20(crv).balanceOf(address(proxy));
        if (amount > 0) proxy.increaseAmount(amount);
    }

    /// @notice Extend veCRV lock time to maximum amount of 4 years.
    function maxLock() external {
        require(msg.sender == governance || lockers[msg.sender], "!locker");
        uint max = now + (365 days * 4);
        uint lock_end = veCRV.locked__end(address(proxy));
        if(lock_end < (max / WEEK) * WEEK){
            proxy.safeExecute(
                address(veCRV), 
                0, 
                abi.encodeWithSignature("increase_unlock_time(uint256)", max)
            );
        }
    }

    /// @notice Vote on a gauge
    /// @param _gauge The gauge to vote on
    /// @param _weight Weight to vote with
    function vote(address _gauge, uint256 _weight) external {
        require(msg.sender == governance || voters[msg.sender], "!voter");
        _vote(_gauge, _weight);
    }

    /// @notice Vote on a multiple gauges
    /// @param _gauges List of gauges to vote on
    /// @param _weights List of weight to vote with
    function vote_many(address[] calldata _gauges, uint256[] calldata _weights) external {
        require(msg.sender == governance || voters[msg.sender], "!voter");
        require(_gauges.length == _weights.length, "!mismatch");
        for(uint256 i = 0; i < _gauges.length; i++) {
            _vote(_gauges[i], _weights[i]);
        }
    }

    function _vote(address _gauge, uint256 _weight) internal {
        proxy.safeExecute(gauge, 0, abi.encodeWithSignature("vote_for_gauge_weights(address,uint256)", _gauge, _weight));
    }

    /// @notice Withdraw exact amount of LPs from gauge
    /// @param _gauge The gauge from which to withdraw
    /// @param _token The LP token to withdraw from gauge
    /// @param _amount The exact amount of LPs with withdraw
    function withdraw(
        address _gauge,
        address _token,
        uint256 _amount
    ) public returns (uint256) {
        require(strategies[_gauge] == msg.sender, "!strategy");
        uint256 _balance = IERC20(_token).balanceOf(address(proxy));
        proxy.safeExecute(_gauge, 0, abi.encodeWithSignature("withdraw(uint256)", _amount));
        _balance = IERC20(_token).balanceOf(address(proxy)).sub(_balance);
        proxy.safeExecute(_token, 0, abi.encodeWithSignature("transfer(address,uint256)", msg.sender, _balance));
        return _balance;
    }

    /// @notice Find Yearn voter's full balance within a given gauge
    /// @param _gauge The gauge from which to check balance
    function balanceOf(address _gauge) public view returns (uint256) {
        return IERC20(_gauge).balanceOf(address(proxy));
    }

    /// @notice Withdraw full balance of voter's LPs from gauge
    /// @param _gauge The gauge from which to withdraw
    /// @param _token The LP token to withdraw from gauge
    function withdrawAll(address _gauge, address _token) external returns (uint256) {
        return withdraw(_gauge, _token, balanceOf(_gauge));
    }

    /// @notice Takes care of depositing Curve LPs into gauge
    /// @dev Strategy must first transfer LPs to this contract prior to calling
    /// @param _gauge The gauge to deposit LP token into
    /// @param _token The LP token to deposit into gauge
    function deposit(address _gauge, address _token) external {
        require(strategies[_gauge] == msg.sender, "!strategy");
        uint256 _balance = IERC20(_token).balanceOf(address(this));
        IERC20(_token).safeTransfer(address(proxy), _balance);
        _balance = IERC20(_token).balanceOf(address(proxy));

        proxy.safeExecute(_token, 0, abi.encodeWithSignature("approve(address,uint256)", _gauge, 0));
        proxy.safeExecute(_token, 0, abi.encodeWithSignature("approve(address,uint256)", _gauge, _balance));
        proxy.safeExecute(_gauge, 0, abi.encodeWithSignature("deposit(uint256)", _balance));
    }

    /// @notice Abstracts the CRV minting and transfers to an approved strategy with CRV earnings
    /// @dev Designed to be called within the harvest function of a strategy
    /// @param _gauge The gauge which this strategy is claiming CRV from
    function harvest(address _gauge) external {
        require(strategies[_gauge] == msg.sender, "!strategy");
        uint256 _balance = IERC20(crv).balanceOf(address(proxy));
        proxy.safeExecute(mintr, 0, abi.encodeWithSignature("mint(address)", _gauge));
        _balance = (IERC20(crv).balanceOf(address(proxy))).sub(_balance);
        proxy.safeExecute(crv, 0, abi.encodeWithSignature("transfer(address,uint256)", msg.sender, _balance));
    }

    function claimToken(address _token) external {
        address recipient = tokenRecipient[_token];
        require(msg.sender == recipient);
        uint256 _balance = IERC20(_token).balanceOf(address(proxy));
        if (_balance > 0) {
            proxy.safeExecute(_token, 0, abi.encodeWithSignature("transfer(address,uint256)", recipient, _balance));
            emit TokenClaimed(_token, recipient, _balance);
        }
    }

    /// @notice Claim share of weekly admin fees from Curve fee distributor
    /// @dev Admin fees become available every Thursday, so we run this expensive logic only once per week.
    /// @param _recipient The address to which we transfer 3CRV
    function claim(address _recipient) external {
        require(msg.sender == feeRecipient, "!approved");
        if (!claimable()) return;

        address p = address(proxy);
        feeDistribution.claim_many([p, p, p, p, p, p, p, p, p, p, p, p, p, p, p, p, p, p, p, p]);
        lastTimeCursor = feeDistribution.time_cursor_of(address(proxy));

        uint256 amount = IERC20(CRV3).balanceOf(address(proxy));
        if (amount > 0) {
            proxy.safeExecute(CRV3, 0, abi.encodeWithSignature("transfer(address,uint256)", _recipient, amount));
            emit AdminFeesClaimed(_recipient, amount);
        }
    }

    /// @notice Check if it has been one week since last admin fee claim
    function claimable() public view returns (bool) {
        /// @dev add 1 day buffer since fees come available mid-day
        if (now < lastTimeCursor.add(WEEK) + 1 days) return false;
        return true;
    }

    /// @notice Claim non-CRV token incentives from the gauge and transfer to strategy
    /// @param _gauge The gauge which this strategy is claiming rewards
    /// @param _token The token to be claimed to the approved strategy
    function claimRewards(address _gauge, address _token) external {
        require(strategies[_gauge] == msg.sender, "!strategy");
        Gauge(_gauge).claim_rewards(address(proxy));
        _transferBalance(_token);
    }

    /// @notice Claim non-CRV token incentives from the gauge and transfer to strategy
    /// @param _gauge The gauge which this strategy is claiming rewards
    /// @param _tokens The token(s) to be claimed to the approved strategy
    function claimManyRewards(address _gauge, address[] memory _tokens) external {
        require(strategies[_gauge] == msg.sender, "!strategy");
        Gauge(_gauge).claim_rewards(address(proxy));
        for (uint256 i; i < _tokens.length; ++i) {
            _transferBalance(_tokens[i]);
        }
    }

    function _transferBalance(address _token) internal {
        proxy.safeExecute(_token, 0, abi.encodeWithSignature("transfer(address,uint256)", msg.sender, IERC20(_token).balanceOf(address(proxy))));
    }
}