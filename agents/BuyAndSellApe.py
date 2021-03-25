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