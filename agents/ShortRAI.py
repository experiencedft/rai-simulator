import math
from random import seed
from random import uniform

class ShortRAI():
    '''
    A class to represent shorters who mint RAI to sell it on the market for ETH when the market price is above the redemption price with a certain delta threshold. These agents make sure that the value of their debt remains below what they could buy on the market at any given point in time to be able to close their safes. When the *effective* market price drops some percentage below their initial mint price, they buy back on the market and close their safes for an ETH profit. Can only have one short opened at a time for now. The price target for now is the redemption price when the short is opened. 

    TODO: Make targets to close the short more varied. Agents might cloes their shorts only when the price market price starts going up again, or might do before their target is reached if they're ok with the current unrealized profit, etc.

    Attributes 
    ___________

    wallet: dictionary[float]
        wallet content of the ape which can take a variety of tokens, every entry initialized to 0 except the ETH content of the wallet, generated at random from a distribution
    difference_threshold: float
        the threshold of (market_price - redemption_price) that the shorter requires before deciding to mint and sell RAI, in %, initialized with the agent at random from a distribution
    stop_loss: float
        if a shorter mints and sell RAI but the price does not immediately move down as they wanted to, they might have a stop loss in place, i.e. if the price of RAI goes up by more than  some %, they would rather realize their loss than have to repay their debt at a higher value if/when they need to unlock their collateral. +inf if no stop loss
    desired_collateralization: float
        the desired collateralization ratio to open the safe with. Lower = more debt generated to sell = more risky
    safes_owned: list[int]
        the unique IDs of the safes owned by the agent
    active_safes_counter: int
        counting the amount of active safes (collateral and debt > 0)
    net_worth_before_shorting: float
        sum of all wallet content in ETH, plus the total (collateral - debt) denominated in ETH across all non-liquidated vaults, active or inactive, right before shorting RAI by opening a new vault
    current_short_price_target: float
        the price target of the current active short = the redemption price at the time of opening the safe



    Methods
    ____________

    updateWallet(net_amount_rai_in, net_amount_eth_in):
        update the wallet of the agent by providing the net amount of each relevant token to add to the wallet
    mint(System, Pool, amount_collateral):
        mint some amount of RAI by using the specified amount of ETH as collateral. 
    isDifferenceAboveThreshold(System, Pool):
        check whether the difference between  the redemption price of the system and the current market price is above the desired threshold = if opening a short is a good idea for that agent now 
    isLossAboveStopLoss(System, Pool):
        verify whether the current unrealized loss of the short is above the stop loss of the user
    isSpotPriceBelowTarget(Pool):
        check whether the current spot price is below the target recorded when opening the short (redemption price of the system at the price of opening the short)
    buyAndRepay(System, Pool):
        buy enough RAI to repay the debt entirely with the ETH left in the wallet and close the safe 
    sellRAI():
        sell whatever amount of RAI present in the wallet in the Uniswap pool (either after minting, or to realize profit after a successful arbitrage)
    '''

    def __init__(self, eth_holdings_distribution, difference_threshold_distribution, stop_loss_distribution, collateralization_distribution):

        self.wallet = {"eth": 0, "rai": 0}

        if eth_holdings_distribution[0] == "uniform": 
            lower_bound = eth_holdings_distribution[1][0]
            upper_bound = eth_holdings_distribution[1][1]
            self.wallet["eth"] = uniform(lower_bound, upper_bound)

        if difference_threshold_distribution[0] == "uniform":
            lower_bound = difference_threshold_distribution[1][0]
            upper_bound = difference_threshold_distribution[1][1]
            self.difference_threshold = uniform(lower_bound, upper_bound)

        if stop_loss_distribution[0] == "uniform": 
            lower_bound = stop_loss_distribution[1][0]
            upper_bound = stop_loss_distribution[1][1]
            self.stop_loss = uniform(lower_bound, upper_bound)

        if collateralization_distribution[0] == "uniform": 
            lower_bound = collateralization_distribution[1][0]
            upper_bound = collateralization_distribution[1][1]
            self.desired_collateralization = uniform(lower_bound, upper_bound)

        self.safes_owned = []
        self.active_safes_counter = 0
        self.net_worth_before_shorting = self.wallet["eth"]
        self.current_short_price_target = 0
        self.type = "ShortRAI"

    def updateWallet(self, net_amount_rai_in, net_amount_eth_in):
        '''
        Add net amount of tokens provided to the wallet. Negative to remove tokens.

        Parameters:

        net_amount_rai_in, net_amount_eth_in: float 
            allowed to be negative
        
        State chance:

        self.wallet: 
            update the wallet of the agent

        Returns:
        
        None
        '''
        self.wallet["rai"] += net_amount_rai_in
        self.wallet["eth"] += net_amount_eth_in

    def isDifferenceAboveThreshold(self, System, Pool, eth_usd_price):
        '''
        Check whether the current gap between  the redemption price of the system and the current market price is above the desired threshold (in %) of the agent. If it is, return True, indicating that it is time to open a short.

        Parameters: 

        System: RAISystem() class

        Pool: UniswapPool() class

        eth_usd_price: 
            the current price of ETH in USD

        State change: 

        None

        Returns: 

        True if the difference is above the threshold, False otherwise 
        '''
        redemption_price_in_usd = System.redemption_price
        spot_price_in_eth = Pool.getSpotPrice()
        redemption_price_in_eth = redemption_price_in_usd/eth_usd_price
        #Negative if the redemption price is above the spot price
        difference_in_percent = 100*(1 - redemption_price_in_eth/spot_price_in_eth)
        if difference_in_percent > self.difference_threshold:
            return True 
        else: 
            return False

    def mint(self, System, Pool, amount_collateral, eth_usd_price):
        '''
        Mint some amount of RAI by using the specified amount of ETH as collateral.

        Parameters: 

        System: RAISystem() class
            the RAI system to use to mint the RAI
        Pool: UniswapPool() class
            the current Uniswap RAI/ETH pool
        amount_collateral: float
            the amount of ETH collateral to open the safe with
        eth_usd_price: float
            the current price of ETH in USD

        State chance: 
        
        System: 
            open a new vault and add collateral and generated debt to total
        self.wallet:
            remove collateral from wallet and add minting RAI

        Returns: 

        None
        '''
        #Check that the user doesn't already have an active safe
        if self.active_safes_counter < 1: 
            safe_id, rai_to_mint = System.openSafe(amount_collateral, self.desired_collateralization, eth_usd_price)
            self.safes_owned.append(safe_id)
            self.updateWallet(rai_to_mint, -amount_collateral)
            self.active_safes_counter +=1
            self.current_short_price_target = System.redemption_price
    
    def buyAndRepay(self, System, Pool, eth_usd_price):
        '''
        Buy the amount of RAI needed to repay the debt and close the safe by repaying the entire debt.

        Parameters: 

        System: RAISystem() class

        Pool: UniswapPool() class

        eth_usd_price: float
            the current price of ETH in USD

        State change: 

        System.safes: 
            delete the safe closed by the agent
        System.total_collateral:
            subtract the collateral of the safe at the time of closing 
        System.total_debt: 
            subtract the debt of the safe at the time of closing
        Pool.reserves: 
            modify the reserves of the pool upon buying RAI
        self.wallet:
            change the wallet content of the agent
        self.active_safes_counter: 
            subtract 1 to active safes counter

        Returns: 

        None
        '''
        #The active safe to close
        active_safe_id = self.safes_owned[-1]
        active_safe = System.getSafe(active_safe_id)
        #The debt to repay
        debt = active_safe["debt"]
        #Amount of ETH needed to buy the necessary amount of RAI 
        eth_needed = Pool.ETHInGivenRAIOut(debt)
        #If the amount of ETH in the wallet is not enough, add the difference! This may represent for example a new fiat -> crypto buy.
        #Note that this does not add anything to the agent's net worth as that difference is only used to repay the debt
        if eth_needed > self.wallet["eth"]:
            self.wallet["eth"] += eth_needed - self.wallet["eth"]
        #Subtract used ETH from wallet
        self.wallet["eth"] -= eth_needed
        #Close the safe
        collateral_withdrawn = System.closeSafe(active_safe_id)
        #Subtract RAI used to close the safe and add ETH obtained from the safe to wallet
        self.wallet["eth"] += collateral_withdrawn
        #All of the RAI was used to repay the debt
        self.wallet["rai"] = 0 
        self.active_safes_counter -= 1  
    
    def sellRAI(self, Pool):
        '''
        Sell all the RAI currently in the wallet into the Uniswap pool.

        Parameters:

        Pool: UniswapPool() class

        State change: 

        Pool.reserves

        self.wallet

        Returns: 

        None
        '''
        eth_obtained = Pool.sellRAI(self.wallet["rai"])
        self.wallet["eth"] += eth_obtained
        self.wallet["rai"] = 0
            
    def isLossAboveStopLoss(self, System, Pool): 
        '''
        Check whether the current unrealized loss of the agent from its starting net worth in ETH before shorting, is above some threshold. If it is, the agent uses that information to repay their debt and close the vault using another method. 

        Parameters: 

        System: RAISystem() class

        Pool: UniswapPool() class

        State change: 

        None

        Returns: 

        True if the current unrealized loss is above threshold, False otherwise.
        '''
        #Current effective value of the debt in ETH (amount needed to repay the debt)
        active_safe = System.getSafe(self.safes_owned[-1])
        amount_eth_needed = Pool.ETHInGivenRAIOut(active_safe["debt"])
        current_net_worth = self.wallet["eth"] + active_safe["collateral"] - amount_eth_needed
        #Current unrealized loss
        unrealized_loss = 100*(1- current_net_worth/self.net_worth_before_shorting)
        if unrealized_loss > self.stop_loss:
            return True
        else: 
            return False

    def isSpotPriceBelowTarget(self, Pool, eth_usd_price): 
        '''
        Check whether the current spot price in the Uniswap pool is below the target when opening the short, i.e. the system's redemption price at the time of minting.
        '''
        spot_price_in_eth = Pool.getSpotPrice()
        target_price_in_usd = self.current_short_price_target
        target_price_in_eth = target_price_in_usd/eth_usd_price
        if spot_price_in_eth < target_price_in_eth:
            return True 
        else: 
            return False