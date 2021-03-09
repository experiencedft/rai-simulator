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
    safes: list[dictionary]
        list of all the open safes as dictionaries, with "collateral", "debt" and "id"
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

