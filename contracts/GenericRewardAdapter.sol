# Claim(gauge, token) + pull to adapter 
# Split logic (recipients, )
# Transfer(partner, stash)

RewardInfo {
    address platform,
    address partnerVoter,
    address partnerRecipient
}

addRewardPath(
    address platform,
    address partner_voter,
    address partner_recipient,
    address token,
    address gauge,
) external onlyGovernance {

}
    platform
    partner

claim(
    address token,
    address gauge,
) external {
    _claim(_gauge, _token);
    
    uint amount = proxy.pullRewards(_gauge, _token);
    _splitAndSend(amount);
}



_splitAndSend(uint amount){
    info = rewardInfo[token][gauge];
    keep = amount
    if(info.parterner_voter != address(0)){
        power = gauge_controller.user_vote.power
        total_vecrv = vecrv.balanceOf(voter)
        yearn_amount = total_vecrv * power / 10_000
        partner_amount = ycrv.balanceOf(parterner_voter) + yveCRV.balanceOf(partner_voter)
        ratio = partner_amount * 10_000 / yearn_amount
        toSend = amount * ratio / 10_000
        if(toSend > 0){
            keep -= toSend;
            token.transfer(info.partner_recipient, toSend);
        }
        token.transfer(stash, keep);
    }

    
}
