import math
from random import seed
from random import uniform

TOTAL_FLX_SUPPLY = 1000000

class BuyAndSellApe():
    '''
    A class to represent one type of agents, the Apes who are buying RAI directly on the market to supply liquidity instead of minting new RAI supply if the APY is above their threshold, and remove liquidity and sell if the APY is below their threshold. At this stage it is assumed that interactions with a Uniswap pool don't incur any fee.

    Attributes 
    ___________

    wallet: dictionary[float]
        wallet content of the ape which can take a variety of tokens, every entry initialized to 0 except the ETH content of the wallet, generated at random from a distribution
    apy_threshold: float
        the apy threshold of the ape that they require before deciding to join the pool, in %, initialized with the agent at random from a distribution
    expected_flx_valuation: float
        the total valuation of FLX in USD expected by the ape, leading to a price in USD per FLX, initilized with the agent at random from an expected valuation distribution


    Methods
    ____________

    updateWallet(net_amount_rai_in, net_amount_eth_in, net_amount_LP tokens_in):
        update the wallet of the ape by providing the net amount of each relevant token to add to the wallet
    isAPYGood(Pool):
        given the current uniswap pool, the ape checks the APY that they would get by buying and providing liquidity, using the effective price of their trade, and whether it is satisfactory
    buyAndProvide(Pool):
        buy as much RAI as possible on the market while still being able to provide liquidity afterwards
    removeAndSell(Pool):
        remove liquidity from the Uniswap pool and sell the RAI in the pool directly
    '''

    def __init__(self, eth_holdings_distribution, apy_threshold_distribution, expected_flx_valuation_distribution):
        '''
        Initialization of the ape. 

        Parameters: 

        eth_holdings_distribution: list[string, list[float]] 

            information about the distribution of eth holdings to draw the ape from. 
            
            First entry is a list describing the type of distribution to draw from. Only supports "uniform" as of now. Later: "gaussian", "pareto"...

            uniform distrib params: min and max in ETH
            gaussian distrib params: mean and std
            pareto distrib params: scale and shape

        apy_threshold_distribution: list[string, list[float]]

            see eth_holdings_distribution, only supports "uniform" for now with min and max in %

        expected_FLX_valuation_distribution: list[string, list[float]]

            see eth_holdings_distribution, only supports "uniform" for now with min and max in USD
        '''

        self.wallet = {"rai": 0, "eth": 0, "lp tokens": 0}

        self.current_apy = 0

        if eth_holdings_distribution[0] == "uniform": 
            lower_bound = eth_holdings_distribution[1][0]
            upper_bound = eth_holdings_distribution[1][1]
            self.wallet["eth"] = uniform(lower_bound, upper_bound)

        if apy_threshold_distribution[0] == "uniform":
            lower_bound = apy_threshold_distribution[1][0]
            upper_bound = apy_threshold_distribution[1][1]
            self.apy_threshold = uniform(lower_bound, upper_bound)

        if expected_flx_valuation_distribution[0] == "uniform": 
            lower_bound = expected_flx_valuation_distribution[1][0]
            upper_bound = expected_flx_valuation_distribution[1][1]
            self.expected_flx_valuation = uniform(lower_bound, upper_bound)

        self.type = "BuyAndSellApe"

    def isAPYGood(self, Pool, System, flx_given_per_day, eth_usd_price):
        '''
        Given the current Uniswap RAI/ETH pool state, check that the APY is satisfactory for the ape, without affecting the state of the pool. If the ape already has LP tokens, the calculation is direct. Otherwise, the ape calculates what their APY would be if they provided liquidity with their entire net worth. ONLY WORKS IF ETH RESERVES IN THE POOL ARE < 2. Note: can be modified later to use part of their net worth instead of its entirety.
        CURRENTLY ONLY WORKS FOR HOURLY SIMULATIONS

        Parameters: 

        Pool: UniswapPool class from uniswap.py
            the current RAI/ETH Uniswap pool

        System: RAISystem class from rai_system.py
            the current RAISystem

        flx_given_per_day: float
            the amount of FLX tokens given per day in total to liquidity providers

        eth_usd_price: float
            the current ETHUSD price

        State change: 

        current_apy: float
            the expected apy calculated by the agent when the method is called

        current_pool_share: float
            the pool share calculated by the agent when the method is called (current pool share or potential pool share)
        
        Returns: 

        isGood: bool
            true if the APY the ape would get is above their threshold, false otherwise
        '''

        if self.wallet["lp tokens"] == 0: 

            #Get useful parameters from current pool state
            liquidity_tokens_supply = Pool.liquidity_tokens_supply
            total_value_locked_in_eth = Pool.getTotalValueLockedInETH()
            eth_reserve = Pool.reserves[1]
            #Calculate what is the maximum amount of ETH the ape should use to be able to provide liquidity with their entire wallet content, see documentation for a proof of this formula which surprisingly doesn't depend on the current RAI reserves. ONLY WORKS IF ETH RESERVES IN THE POOL ARE < 2.
            amount_eth_to_buy_with = eth_reserve*(math.sqrt(1 + self.wallet["eth"]/eth_reserve) - 1)
            #Calculate amount of liquidity tokens that would be obtained
            liquidity_tokens_obtained = Pool.virtualAddLiquidityAfterBuyingRAI(amount_eth_to_buy_with)
            #New liquidity tokens supply that would result from this interaction
            new_liquidity_tokens_supply = liquidity_tokens_supply + liquidity_tokens_obtained
            #Portion of the pool that the ape would represent after buying and providing liquidity
            pool_share = liquidity_tokens_obtained/new_liquidity_tokens_supply
            #The value of the FLX drop that the ape expects will be given to LPs per day
            total_value_awarded_per_day_in_usd = self.expected_flx_valuation*(flx_given_per_day/TOTAL_FLX_SUPPLY)
            #The value that the ape gets
            value_awarded_to_ape_per_day_in_usd = pool_share*total_value_awarded_per_day_in_usd
            extrapolated_reward_per_year_in_usd = value_awarded_to_ape_per_day_in_usd*365
            #Calculate APY in %
            value_of_pool_share_in_usd = total_value_locked_in_eth*eth_usd_price*pool_share
            #The APY is the value reward gotten plus the system's APY (annualized redemption rate) which can be negative
            #Get current system redemption price and pool spot price
            redemption_price = System.redemption_price
            redemption_rate_hourly = System.redemption_rate_hourly
            market_price_in_eth = Pool.getSpotPrice()
            market_price_in_usd = market_price_in_eth*eth_usd_price
            #Convert hourly redemption rate from RAI.h-1 to (proportion).h-1, i.e. 0.10 = 10%
            redemption_rate_hourly_proportion = (redemption_rate_hourly/redemption_price)
            extrapolated_future_redemption_price = redemption_price*(1+redemption_rate_hourly_proportion)**8760
            if redemption_rate_hourly_proportion > 0:
                system_apy = 100*abs(1 - extrapolated_future_redemption_price/market_price_in_usd)
            else: 
                system_apy = -100*abs(1 - extrapolated_future_redemption_price/market_price_in_usd)
            apy = (extrapolated_reward_per_year_in_usd/value_of_pool_share_in_usd - 1)*100 + system_apy
            self.current_apy = apy
            self.current_pool_share = pool_share
            
        else: 

            #Get useful parameters from current pool state
            liquidity_tokens_supply = Pool.liquidity_tokens_supply
            total_value_locked_in_eth = Pool.getTotalValueLockedInETH()
            pool_share = self.wallet["lp tokens"]/liquidity_tokens_supply
            #The value of the FLX drop that the ape expects will be given to LPs per day
            total_value_awarded_per_day_in_usd = self.expected_flx_valuation*(flx_given_per_day/TOTAL_FLX_SUPPLY)
            #The value that the ape gets
            value_awarded_to_ape_per_day_in_usd = pool_share*total_value_awarded_per_day_in_usd
            extrapolated_reward_per_year_in_usd = value_awarded_to_ape_per_day_in_usd*365
            #Calculate APY in %
            value_of_pool_share_in_usd = total_value_locked_in_eth*eth_usd_price*pool_share
            #The APY is the value reward gotten plus the system's APY (annualized redemption rate) which can be negative
            #Get current system redemption price and pool spot price
            redemption_price = System.redemption_price
            market_price_in_eth = Pool.getSpotPrice()
            market_price_in_usd = market_price_in_eth*eth_usd_price
            redemption_rate_hourly = System.redemption_rate_hourly
            #Convert hourly redemption rate from RAI.h-1 to (proportion).h-1, i.e. 0.10 = 10%
            redemption_rate_hourly_proportion = (redemption_rate_hourly/redemption_price)
            extrapolated_future_redemption_price = redemption_price*(1+redemption_rate_hourly_proportion)**8760
            if redemption_rate_hourly_proportion > 0:
                system_apy = 100*abs(1 - extrapolated_future_redemption_price/market_price_in_usd)
            else: 
                system_apy = -100*abs(1 - extrapolated_future_redemption_price/market_price_in_usd)
            apy = (extrapolated_reward_per_year_in_usd/value_of_pool_share_in_usd - 1)*100 + system_apy
            self.current_apy = apy
            self.current_pool_share = pool_share

        if (apy >= self.apy_threshold):
            return True
        else: 
            return False

    def buyAndProvide(self, Pool): 
        '''
        Use exactly the amount of ETH from the wallet needed to buy RAI in the provided Uniswap pool to be able to then provide liquidity with the entirety of the ape's ETH and RAI holdings. In other words, use the ape's entire net worth to provide liquidity.
        
        Parameters: 

        Pool: UniswapPool class from uniswap.py
            the current RAI/ETH Uniswap pool

        State change: 

        self.wallet:
            updates the wallet of the ape to the new holdings - subtract amount of ETH used and add LP tokens obtained

        Pool.reserves: 
            updated by the Pool.addLiquidity method

        Pool.liquidity_tokens_supply:
            updated by the Pool.addLiquidity method 

        Returns:

        None
        '''

        #See isAPYGood method for explanation 
        eth_reserve = Pool.reserves[1]
        amount_eth_to_buy_with = eth_reserve*(math.sqrt(1 + self.wallet["eth"]/eth_reserve) - 1)
        amount_rai_obtained = Pool.buyRAI(amount_eth_to_buy_with)
        #Update wallet ETH holdings
        self.wallet["eth"] -= amount_eth_to_buy_with
        #Add liquidity
        liquidity_tokens_obtained = Pool.addLiquidity(amount_rai_obtained, self.wallet["eth"])
        #Add liquidity tokens obtained to ape's wallet
        self.wallet["lp tokens"] += liquidity_tokens_obtained
        #Update wallet ETH holdings
        self.wallet["eth"] = 0

    def removeAndSell(self, Pool):
        '''
        Remove all of the ape's liquidity in the pool and sell all the RAI obtained on the market immediately. 

        Parameters:

        Pool: UniswapPool class from uniswap.py
            the current RAI/ETH Uniswap pool
        
        State change: 

        self.wallet: 
            updates the wallet of the ape to the new holdings - subtract all LP tokens and add amount of ETH obtained when everything is done

        Pool.reserves: 
            updated by the Pool.removeLiquidity method

        Pool.liquidity_tokens_supply:
            updated by the Pool.removeLiquidity method 
        '''

        #Remove liquidity
        amount_rai, amount_eth = Pool.removeLiquidity(self.wallet["lp tokens"])
        #Sell RAI obtained and add the ETH obtained to the current amount held by the ape 
        amount_eth += Pool.sellRAI(amount_rai)
        #Set LP tokens in the wallet to 0 and add the total amount of ETH obtained
        self.wallet["eth"] += amount_eth
        self.wallet["lp tokens"] = 0 

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