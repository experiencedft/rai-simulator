import math
from random import seed
from random import uniform

class LongETH():
    '''
    A class to represent agents that go long ETH using the RAI system based on the ETH price action. It is assumed that long open interest is a lagging indicator of ETH price action: after a certain period of time that the agent subjectively considers long enough, they open a leveraged long position on ETH and keep that position open until they the price starts to go down for some period of time *or* after their stop loss is hit *or* if they're close to liquidation with "close" being another subjective parameter. These are "traders", meaning that they have stop losses in place and don't play with fire too much, as opposed to holders or "believers" who would keep their longs open, and even replenish even when they're getting close to liquidation.

    This is essentially the same agent as the RAI short, except that their decision criterion is not based on the state of the RAI system, but only on the ETH price action (their decisions and actions can thus be parallelized).

    TODO: 
    
    - Include the possibility of getting higher leverage. Problem: the maximum possible leverage isn't trivial to calculate.

    - Implement more complex trading strategies based on RSI or other voodoo TA crystal ball stuff.
    

    Attributes 
    ___________

    wallet: dictionary[float]
        wallet content of the ape which can take a variety of tokens, every entry initialized to 0 except the ETH content of the wallet, generated at random from a distribution
    stop_loss: float
        the agents' stop loss if the price of Ethereum is going down
    desired_leverage: float
        the desired leverage ratio of the agents
    safes_owned: list[int]
        the unique IDs of the safes owned by the agent
    uptrend_to_open_long: list[int, float]
        number of days in a row where ETH goes up more than X% to open a long position
    downtrend_to_close_long: list[int, float]
        number of days in a row where ETH goes down more than X% to close a long position
    liquidation_protection_threshold: float
        the difference in percentage point between the critical liquidation collateralization ratio and the current collateralization at which the agent considers the position critical and closes it
    active_safes_counter: int
        counting the amount of active safes (collateral and debt > 0)
    net_worth_before_longing: float
        sum of all wallet content in ETH, plus the total (collateral - debt) denominated in ETH across all non-liquidated vaults, active or inactive, right before longing ETH by opening a new vault
    
    
    Methods
    ___________

    mint(System, Pool, amount_collateral):
        mint some amount of RAI by using the specified amount of ETH as collateral. 
    sellRAI():
        sell whatever amount of RAI present in the wallet in the Uniswap pool to leverage ETH
    isLossAboveStopLoss(System, Pool):
        verify whether the current unrealized loss of the short is above the stop loss of the user
    buyAndRepay(System, Pool):
        buy enough RAI to repay the debt entirely with the ETH left in the wallet and close the safe 
    isUptrendGoodToLong(eth_price_arary):
        verify whether the current uptrend is looking good to the agent to open a long
    isDowntrendBad(eth_price_array):
        verify whether the current downtrend is looking bad to the agent in which case they close their long
    isCloseToLiquidation(System):
        verify whether the current active safe is close to liquidation, in which case the agent would close their long
    '''

    def __init__(self, eth_holdings_distribution, uptrend_to_open_long_distribution, downtrend_to_close_long_distribution, stop_loss_distribution):

        self.wallet = {"eth": 0, "rai": 0}

        if eth_holdings_distribution[0] == "uniform": 
            lower_bound = eth_holdings_distribution[1][0]
            upper_bound = eth_holdings_distribution[1][1]
            self.wallet["eth"] = uniform(lower_bound, upper_bound)

        if uptrend_to_open_long_distribution[0] == "uniform":
            lower_bound = uptrend_to_open_long_distribution[1][0]
            upper_bound = uptrend_to_open_long_distribution[1][1]
            #It's a number of days = int
            self.uptrend_to_open_long = int(uniform(lower_bound, upper_bound))

        if downtrend_to_close_long_distribution[0] == "uniform":
            lower_bound = downtrend_to_close_long_distribution[1][0]
            upper_bound = downtrend_to_close_long_distribution[1][1]
            #See above
            self.downtrend_to_close_long = int(uniform(lower_bound, upper_bound))

        if stop_loss_distribution[0] == "uniform": 
            lower_bound = stop_loss_distribution[1][0]
            upper_bound = stop_loss_distribution[1][1]
            self.stop_loss = uniform(lower_bound, upper_bound)

        self.safes_owned = []
        self.active_safes_counter = 0
        self.net_worth_before_longing = self.wallet["eth"]
        self.current_short_price_target = 0
        self.type = "LongETH"

    def updateWallet(self, net_amount_rai_in, net_amount_eth_in):
        '''
        Add net amount of tokens provided to the wallet. Negative to remove tokens.

        Parameters:

        net_amount_rai_in, net_amount_eth_in: float 
            allowed to be negative
        
        State change:

        self.wallet: 
            update the wallet of the agent

        Returns:
        
        None
        '''
        self.wallet["rai"] += net_amount_rai_in
        self.wallet["eth"] += net_amount_eth_in

    def netAddCollateral(self, System, net_amount_collateral_to_add, eth_usd_price):
        '''
        Add the amount of collateral specified to the active safe.

        Parameters: 

        System: RAISystem() class

        amount_to_add: float
            amount of collateral to add in ETH

        State change: 

        self.wallet
        System.safes
        ''' 
        System.modifySafe(self.safes_owned[-1], net_amount_collateral_to_add, 0, eth_usd_price)
        self.wallet["eth"] -= net_amount_collateral_to_add


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
        self.active_safes_counter
        self.safes_owned

        Returns: 

        None
        '''
        #Check that the user doesn't already have an active safe
        if self.active_safes_counter < 1: 
            safe_id, rai_to_mint = System.openSafe(amount_collateral, 145.01, eth_usd_price)
            self.safes_owned.append(safe_id)
            self.updateWallet(rai_to_mint, -amount_collateral)
            self.active_safes_counter +=1
            self.current_short_price_target = System.redemption_price

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
        Check whether the current unrealized loss of the agent from its starting net worth in ETH before longing is above some threshold. If it is, the agent uses that information to repay their debt and close the safe using another method. 

        Parameters: 

        System: RAISystem() class

        Pool: UniswapPool() class

        State change: 

        None

        Returns: 

        True if the current unrealized loss is above threshold, False otherwise.
        '''
        #Current effective value of the debt in ETH (amount needed to repay the debt)
        if self.active_safes_counter > 0:
            active_safe = System.getSafe(self.safes_owned[-1])
            amount_eth_needed = Pool.ETHInGivenRAIOut(active_safe["debt"])
            current_net_worth = self.wallet["eth"] + active_safe["collateral"] - amount_eth_needed
            #Current unrealized loss
            unrealized_loss = 100*(1- current_net_worth/self.net_worth_before_longing)
            if unrealized_loss > self.stop_loss:
                return True
            else: 
                return False

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

    def isUptrendGoodToLong(self, eth_price_array_hourly):
        '''
        Check whether the agent finds the current price trend good to long. Currently a number of weeks in a row of positive price action.

        Return True if it is.

        Return False otherwise.
        '''

        for i in range(self.uptrend_to_open_long, 0, -1):
            if (eth_price_array_hourly[-168*(i+1)] < eth_price_array_hourly[-168*i]) == False:
                return False
        return True

    def isDowntrendBad(self, eth_price_array_hourly):
        '''
        Check whether the agent finds the current price trend bad enough that they want to close their long. Curently a number of days in a row of positive price action.

        Return True if it is.

        Return False otherwise.
        '''

        for i in range(self.downtrend_to_close_long, 0, -1):
            if (eth_price_array_hourly[-168*(i+1)] > eth_price_array_hourly[-168*i]) == False:
                return False
        return True
    
    def isCloseToLiquidation(self, System, eth_usd_price):
        '''
        Check whether the active vault owned by the agent is close to being liquidated, defined as a collateralization ratio lower than 150%.

        Return True if it is.

        Return False otherwise.
        '''
        if self.active_safes_counter > 0:
            safe = System.getSafe(self.safes_owned[-1])
            collateral_in_eth = safe["collateral"]
            debt_in_rai = safe["debt"]
            debt_in_eth = debt_in_rai*(System.redemption_price/eth_usd_price)
            collateralization_percent = 100*(collateral_in_eth/debt_in_eth)
            if collateralization_percent < 150:
                return True
            return False