import math

class UniswapPool(): 
    '''
    A class to represent the RAI/ETH Uniswap pool's state with all the methods to interact with it, assuming that there are no fees anywhere.

    Attributes
    ___________

    reserves: list[float]
        the reserves of the pool in RAI and ETH
    liquidity_tokens_supply: float
        the total supply of liquidity tokens
    total_value_locked: float
        the total value of the pool in ETH
    hourly_prices: list[float]
        for simulations with 1 hour time units, the RAI/ETH price at the end of each 1 hour slot for the past 16 hours
    initial_spot_price: float
        the initial spot price of the pool

    Methods
    ___________
    
    addLiquidity(amount_rai, amount_eth):
        add specified liquidity to the pool and return the amount of liquidity tokens to mint while updating the supply
    virtualAddLiquidity(amount_rai, amount_eth):
        get the amount of liquidity tokens that would be given, given an amount of RAI and ETH in, without changing the state of the pool
    removeLiquidity(lp_tokens):
        remove liquidity corresponding to a given amount of LP tokens, remove these liquidity tokens from the total supply, return the amount of RAI and ETH to give to the user
    buyRAI(amount_eth):
        buy some amount of RAI with amount_eth
    virtualBuyRAI(amount_eth):
        get the amount of RAI that one could buy with a given amount of ETH without changing the state of the pool
    sellRAI(amount_rai):
        sell amount_rai for eth
    getSpotPrice():
        get the current spot RAI/ETH price of the pool 
    getTotalValueLockedInETH():
        get the total value locked in the pool in ETH
    addHourlyPrice(end_price):
        add the hourly price at the end of a 1-hour period to the list
    getTWAP():
        get the current 16 hours time-weighted average RAI/ETH price of the pool  
    '''

    def __init__(self, initial_rai, initial_eth):
        '''
        Initialize the pool with the given amount of RAI and ETH. 
        '''
        self.reserves = [initial_rai, initial_eth]
        self.hourly_prices = []
        #To be consistent with the initialization of liquidity tokens supply in Uniswap v2
        self.liquidity_tokens_supply = math.sqrt(initial_rai*initial_eth)
        self.initial_spot_price = initial_eth/initial_rai

    def getSpotPrice(self):
        '''
        Returns the current RAI/ETH spot price in the pool
        '''
        rai_reserve = self.reserves[0]
        eth_reserve = self.reserves[1]
        return eth_reserve/rai_reserve

    
    def addLiquidity(self, amount_rai, amount_eth):
        '''
        Adds the specified amount of each token to the pool.

        State change: 

        self.reserves: 
            updates to new reserves
        self.liquidity_tokens_supply: 
            updates to new liquidity tokens supply

        Returns: 

        liquidity_tokens_to_mint: 
            an amount of LP tokens representing the share of the pool of the user who called this method.
        
        '''
        assert amount_rai > 0 and amount_eth > 0 
        #Math precision issues, don't do that check
        #assert amount_eth == amount_rai*spot_price_rai_eth

        #Calculate amount of liquidity tokens to mint
        rai_reserves = self.reserves[0]
        liquidity_tokens_to_mint = (amount_rai/rai_reserves)*self.liquidity_tokens_supply

        #Update reserves with new liquidity
        self.reserves[0] += amount_rai
        self.reserves[1] += amount_eth

        #Update liquidity tokens supply
        self.liquidity_tokens_supply += liquidity_tokens_to_mint

        return liquidity_tokens_to_mint

    def virtualAddLiquidity(self, amount_rai, amount_eth):
        '''
        Get the amount of liquidity tokens that *would be minted*, given the arguments, without changing the state of the pool.

        State change: 

        None

        Returns: 

        liquidity_tokens_to_mint: 
            the amount of LP tokens that would be given to the user if they added liquidity with the given arguments
        '''
        assert amount_rai > 0 and amount_eth > 0
        #Math precision issues, don't do that check
        #spot_price_rai_eth = self.getSpotPrice()
        #assert amount_eth == amount_rai*spot_price_rai_eth

        #Calculate amount of liquidity tokens to mint
        rai_reserves = self.reserves[0]
        liquidity_tokens_to_mint = (amount_rai/rai_reserves)*self.liquidity_tokens_supply

        return liquidity_tokens_to_mint

    def virtualAddLiquidityAfterBuyingRAI(self, amount_eth_to_buy_with):
        '''
        Get the amount of liquidity tokens that *would be minted*  if the user bought RAI with some amount of ETH, and then adds liquidity with the amount of RAI bought and the corresponding valid amount of ETH

        Parameters: 

        amount_eth_to_buy_with: float
            the amount of ETH that the user will use to buy RAI with in the current pool
        
        amount_eth_to_add: float
            the amount of ETH that the user will use 

        State change: 

        None

        Returns: 

        liquidity_tokens_to_mint: 
            the amount of LP tokens that would be given to the user if they added liquidity with the given arguments
        '''
        #Save the current state of the pool to revert to it afterwards
        current_reserves = self.reserves.copy()
        current_liquidity_tokens_supply = self.liquidity_tokens_supply

        #We buy RAI with some specified amount of ETH, momentarily changing the state of the pool to be able to carry on with our calculations 
        amount_rai_obtained = self.buyRAI(amount_eth_to_buy_with)

        #Check that the amount of ETH to add is balanced with the amount of RAI obtained, given the new spot price of the pool
        new_spot_price = self.getSpotPrice()
        #Calculate the amount of ETH to add if we want to add all of the obtained RAI
        amount_eth_to_add = new_spot_price*amount_rai_obtained

        #Add the liquidity and get the amount of LP tokens that we would get
        liquidity_tokens_to_mint = self.addLiquidity(amount_rai_obtained, amount_eth_to_add)

        #Revert the pool state to its original state since this function is only used to perform a check
        self.reserves = current_reserves.copy()
        self.liquidity_tokens_supply = current_liquidity_tokens_supply

        return liquidity_tokens_to_mint

    def removeLiquidity(self, liquidity_tokens):
        '''
        Remove tokens from the reserves corresponding to the amount of liquidity tokens given. 

        Parameters: 

        liquidity_tokens: 
            Amount of liquidity tokens to redeem. 

        State change: 

        self.reserves: 
            subtract withdraw amount from reserves
        self.liquidity_tokens_supply: 
            subtract liquidity tokens provided from total supply

        
        Returns: 

        amount_rai, amount_eth: 
            the amount of tokens corresponding to the liquidity tokens burned, to be given to the user calling the method
        '''

        assert liquidity_tokens > 0

        #Calculate amount to give to the user
        rai_reserve = self.reserves[0]
        eth_reserve = self.reserves[1]
        amount_rai = (liquidity_tokens/self.liquidity_tokens_supply)*rai_reserve
        amount_eth = (liquidity_tokens/self.liquidity_tokens_supply)*eth_reserve

        #Update reserves and liquidity tokens supply
        self.reserves[0] -= amount_rai
        self.reserves[1] -= amount_eth
        self.liquidity_tokens_supply -= liquidity_tokens

        return amount_rai, amount_eth

    def buyRAI(self, amount_eth):
        '''
        Buy RAI in the pool with ETH.

        Parameter:

        amount_eth:
            amount of eth to exchange for RAI

        State change: 

        self.reserves: 
            add given amount of ETH
            subtract corresponding amount of RAI
            
        Returns: 

        amount_rai:
            the amount to give to the user
        '''

        assert amount_eth > 0

        #Get invariant
        invariant = self.reserves[0]*self.reserves[1]
        #Update ETH reserve
        self.reserves[1] += amount_eth 
        #Save current RAI reserve
        prev_rai_reserve = self.reserves[0]
        #Get new amount of RAI in the pool
        new_rai_reserve = invariant/self.reserves[1]
        #Update RAI reserve
        self.reserves[0] = new_rai_reserve

        #The new RAI reserve is necessarily lower than the previous ones
        return prev_rai_reserve - new_rai_reserve
    
    def virtualBuyRAI(self, amount_eth):
        '''
        Get the amonunt of RAI that would be given to the user given an amount of ETH.

        Parameter:

        amount_eth:
            amount of eth to exchange for RAI

        State change: 

        None
            
        Returns: 

        amount_rai:
            the amount that would be given to the user
        '''

        assert amount_eth > 0

        #Get invariant
        invariant = self.reserves[0]*self.reserves[1]
        #The new reserves if the trade was executed
        new_eth_reserve = self.reserves[1] + amount_eth 
        #Current RAI reserves
        prev_rai_reserve = self.reserves[0]
        #Get new amount of RAI in the pool
        new_rai_reserve = invariant/new_eth_reserve

        #The new RAI reserve is necessarily lower than the previous ones
        return prev_rai_reserve - new_rai_reserve

    def sellRAI(self, amount_rai):
        '''
        Sell RAI for ETH in the pool.

        Parameter:

        amount_rai:
            amount of rai to sell for ETH

        State change: 

        self.reserves: 
            add given amount of RAI
            subtract corresponding amount of ETH
            
        Returns: 

        amount_eth:
            the amount to give to the user
        '''

        assert amount_rai > 0

        #Get invariant
        invariant = self.reserves[0]*self.reserves[1]
        #Update RAI reserves
        self.reserves[0] += amount_rai
        #Save current ETH reserve
        prev_eth_reserve = self.reserves[1]
        #Get new amount of ETH in the pool
        new_eth_reserve = invariant/self.reserves[0]
        #Update ETH reserve
        self.reserves[1] = new_eth_reserve

        #The new ETH reserve is necessarily lower than the previous one
        return prev_eth_reserve - new_eth_reserve

    def getTotalValueLockedInETH(self): 
        '''
        Get the total value locked in the pool denominated in ETH

        Returns: 

        total_value_locked: 
            the total amount of ETH that the pool is worth
        '''
        rai_reserve = self.reserves[0]
        eth_reserve = self.reserves[1]
        rai_eth_spot_price = self.getSpotPrice()
        total_value_locked = rai_reserve*rai_eth_spot_price + eth_reserve

        return total_value_locked

    def addHourlyPrice(self, end_price):
        '''
        Only use when running simulations that can be divided in one hour periods. Add the price at the end of a one hour period to the hourly_prices attribute, with a limited of 16 prices stored (past 16 hours). 

        Parameter:

        end_price: 
            price at the end of the current one hour period of the simulation

        State change: 

        self.hourly_prices:
            either directly adds the end price to the array, or remove the first element before adding it
        '''
        if len(self.hourly_prices) < 16:
            self.hourly_prices.append(end_price)
        else: 
            hourly_prices = self.hourly_prices.copy()
            removed_first_elem = hourly_prices[1:len(self.hourly_prices)]
            removed_first_elem.append(end_price)
            self.hourly_prices = removed_first_elem

    def getTWAP(self):
        '''
        Only use when running simulations that can be divided in one hour periods. Get the 16-hours time weighted average with one sample per hour, in ETH per RAI

        Returns: 

        time_weighted_average_price:
            the average price over the past 16 hours with one sample per hour period (the end price of that period) in ETH per RAI
        '''
        hourly_prices = self.hourly_prices
        if len(hourly_prices) < 16:
            return self.initial_spot_price
        return sum(hourly_prices)/16

    def ETHInGivenRAIOut(self, amount_rai_out):
        '''
        Returns the amount of ETH needed to get a specific amount of RAI out.
        '''
        #Current ETH Balance
        eth_reserve = self.reserves[1]
        rai_reserve = self.reserves[0]
        #See Balance whitepaper for formula
        eth_needed = eth_reserve*((rai_reserve/(rai_reserve-amount_rai_out)) - 1)

        return eth_needed