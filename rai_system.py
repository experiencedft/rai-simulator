import sys

#Minimum collateralization requirement in %
MIN_COLLATERALIZATION = 145

class RAISystem():
    '''
    A class to represent the RAI system and all of its methods and attributes, such as the total RAI in circulation, the redemption price, the controller acting on the redemption price, etc. The controller is passed as a list whose entries are the type of controllers (string) and its parameters (list), which is read when calling the method to updte the controller. Assumes no stability fee at first.

    Attributes
    ___________

    redemption_price: float
        current redemption price in USD
    redemption_rate_hourly: float
        current hourly redemption rate in RAI.s^-1
    total_debt: float
        total RAI debt issued by the system
    total_collateral: float
        total ETH collateral in custody of the system
    safes: dictionary{dictionary}
        list of all the open safes as dictionaries, with "collateral" and "debt"
    safe_id_counter: int
        a counter keeping track of the number of safes opened to attribute them a unique ID
    max_rai_per_eth: float
        maximum amount of RAI that can currently be issued per unit of collateral
    controller: list[string, list[float]]
        the controller used for the current RAI system

    Methods
    ___________

    openSafe(collateral, collateralization):
        open a safe with the provided amount of collateral and the desired collateralization, update the system accordingly and return the amount of RAI debt issued as well as a safe ID
    closeSafe(safeID):
        close the safe with the given ID and 
    updateRedemptionRate(twap): 
        update the redemption rate under the action of the controller fed with  the current TWAP 
    updateRedemptionPrice(redemption_price, redemption rate):
        update the redemption price based on the previous redemption price and redemption rate
    updateMaxRaiPerEth(current_eth_usd_price):
        update the max RAI that one can get from a unit of ETH collateral given the new ETHUSD price
    '''

    def __init__(self, controller, initial_redemption_price, current_eth_usd_price):
        '''
        Initialization of the RAI system with a given type of controller and an initial redemption price.

        Parameters: 

        controller: list[string, list[float]]
            the type of controller to use fo this system and its parameters. For example, ["P", [Kp]] or ["PI", [Kp, Ki]]
        initial_redemption_price: float 
            the initial redemption price of the system
        current_eth_usd_price: float
            the current ETHUSD price to determine the initial maximum amount of RAI per ETH that can be obtained 

        '''
        
        assert controller[0] == "P" or controller[0] == "PI" or controller[0] == "PID"

        if controller[0] == "P":
            assert len(controller[1]) == 1
        if controller[0] == "PI":
            assert len(controller[1]) == 2
        if controller[0] == "PID":
            assert len(controller[1]) == 3

        self.controller = controller
        self.redemption_price = initial_redemption_price
        self.redemption_rate_hourly = 0
        self.total_collateral = 0
        self.total_debt = 0
        self.safes = {}
        self.safe_id_counter = 0
        self.max_rai_per_eth = (current_eth_usd_price/(MIN_COLLATERALIZATION/100))/initial_redemption_price

    def updateRedemptionRateHourly(self, twap, eth_usd_price):
        '''
        Given a twap, update the redemption rate to the appropriate value by letting the controller act.

        Parameters: 

        twap: float
            the current time weighted average price
        
        State change:

        self.redemption_rate_hourly

        Returns: 

        None
        '''

        #Action of a proportional controller
        if self.controller[0] == "P":
            Kp = self.controller[1][0]
            self.redemption_rate_hourly = Kp*(self.redemption_price - twap*eth_usd_price)
        #Add action of other controllers later
        else:
            assert False

    def updateRedemptionPriceHourly(self):
        '''
        Update the redemption price at the start of a new time period based on the previous redemption rate.

        Parameters: 

        None
        
        State change:

        self.redemption_price

        Returns: 

        None
        '''
        self.redemption_price += self.redemption_rate_hourly
        if self.redemption_price < 0:
            sys.exit("Error: The redemption price is below 0")

    def openSafe(self, collateral, collateralization, eth_usd_price):
        '''
        Open a safe with the specified amount of collateral and generate new RAI debt.

        Parameters: 

        collateral: float
            the amount of collateral to use to open the Safe
        collateralization: float
            the desired collateralization ratio in %
        eth_usd_price: float
            the price of ETH in USD at the time of the safe creation

        State change: 
        
        self.safes: 
            add the safe to the system state
        self.safe_id_counter: 
            increase the safe_id_counter value
        self.total_collateral:
            add collateral to total collateral
        self_total_debt:
            add generated debt to total debt
        
        Returns: 
        
        safe_id: int
            the unique ID of the opened safe
        rai_to_mint: float
            the amount of RAI minted from the safe creation
        '''

        assert collateralization > MIN_COLLATERALIZATION

        safe_id = self.safe_id_counter
        safe_id = str(safe_id)
        rai_to_mint = (collateral*eth_usd_price/(collateralization/100))/self.redemption_price
        self.safes[safe_id] = {"collateral": collateral, "debt": rai_to_mint}
        self.safe_id_counter += 1
        self.total_collateral += collateral
        self.total_debt += rai_to_mint

        return safe_id, rai_to_mint

    def closeSafe(self, safe_id):
        '''
        Close a safe by deleting the safes dictionary entry corresponding to the given ID and giving to the user the collateral remaining after the closing.

        Parameters: 

        safe_id: int
            the unique ID of the safe to close

        State change:

        self.safes: 
            remove the requested safe
        self.total_collateral:
            subtract the collateral of the safe at the time of closing 
        self.total_debt: 
            subtract the debt of the safe at the time of closing

        Returns: 

        outstanding_collateral: float
            the amount of collateral remaining after closing the safe
        '''

        safe_id = str(safe_id)
        collateral = self.safes[safe_id]["collateral"]
        debt = self.safes[safe_id]["debt"]
        self.total_collateral -= collateral
        self.total_debt -= debt
        del self.safes[safe_id]

        return collateral

    def modifySafe(self, safe_id, net_amount_collateral_to_add, net_amount_debt_to_add, eth_usd_price):
        '''
        Modify a safe by either adding or removing collateral or debt. Negative inputs correspond to a removal of that amount.

        Parameters:

        safe_in: int
            the unique ID of the safe to modify

        net_amount_collateral_to_add: float

        net_amount_debt_to_add: float

        eth_usd_price: float

        State change: 

        self.safes: 
            modify the requested safe
        
        self.total_collateral: 
            add net amount of collateral
        
        self.total_debt:
            add net amount of debt

        Returns: 

        None
        '''

        safe_id = str(safe_id)
        self.safes[safe_id]["collateral"] += net_amount_collateral_to_add
        self.safes[safe_id]["debt"] += net_amount_debt_to_add

        #Check that the debt is above the minimum collateralization threshold
        new_collateralization =  self.safes[safe_id]["collateral"]*eth_usd_price/(self.safes[safe_id]["debt"]*self.redemption_price)

        assert new_collateralization > MIN_COLLATERALIZATION

    def getSafe(self, safe_id):
        '''
        Given a safe ID, return a dictionary whose entries are the current collateral and debt of the corresponding safe.

        Parameters: 

        safe_id: int
            the ID of the safe to return
        '''
        return self.safes[str(safe_id)]