# yvCRV + yvBOOST Re-Design

## Overview
- 3CRV rewards to be routed to yvBOOST strategy
- yveCRV now earns no native yield 
- as a result, user can now safely LP their yveCRV without having their rewards lost forever to the pool contract.
- yvBOOST will have direct access to 100% of weekly 3CRV rewards which it will autocompound to more yveCRV

## Contracts in this Repo
1. StrategyProxy.sol
    - This is a modifcation of an already existing contract (deployed at [`0xA420A63BbEFfbda3B147d0585F1852C358e2C152`](https://etherscan.io/address/0xa420a63bbeffbda3b147d0585f1852c358e2c152))
    - Redeploy required in order to achieve our design goal
    - This contract is extremely sensitive as it has access to make arbitrary low-level calls on Yearn's high-value [Voter](https://etherscan.io/address/0xf147b8125d2ef93fb6965db97d6746952a133934#readContract).
    - Change Log:
        - 3CRV rewards can now be re-routed based on new `feeRecipient` variable
        - Events added to help track access control updates and misc changes
        - `vote_many` helper function added
    - Natspec added


2. StrategyYvBOOST.sol
    - This strategy will be added to the yvBOOST vault and will be configured to receive all weekly 3CRV admin fees earned by Yearn's voter via the new `feeRecipient` variable in the StrategyProxy.
    - Claims are checked and made during harvest as well as via direct call from any vault managers.

3. yveCRV.sol
    - This contract is a copy of the already deployed version and is included as a reference only.
    - A design goal is to keep all of yveCRV's key functionality alive without causing reverts or degraded UX. Users should be able to use the following functions just as they did prior to our changes: `deposit`, `transfer`, `claim`, `claimFor`, `update`.
    - After launch, governance multisig will update the following parameters to complete the design
    ```
    yveCrv.setProxy(strategy_proxy)
    yveCrv.setFeeDistribution(ZERO_ADDRESS)
    ```
