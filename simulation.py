from configparser import ConfigParser

import rai_system
import agents
import uniswap

import random 
from datetime import datetime
import os

import matplotlib.pyplot as plt 

#Import config
config_object = ConfigParser()
config_object.read("config.ini")

#Number of agents to interact with the system
N_AGENTS = int(config_object.get("Global parameters", "N_AGENTS"))
ETH_USD_PRICE = float(config_object.get("Global parameters", "ETH_USD_PRICE"))
N_DAYS = int(config_object.get("Global parameters", "N_DAYS"))
N_HOURS = N_DAYS*24
FLX_PER_DAY_LIQUIDITY_PROVIDERS = float(config_object.get("Global parameters", "FLX_PER_DAY_LIQUIDITY_PROVIDERS"))

initial_rai = float(config_object.get("Initial Uniswap pool", "INITIAL_POOL_RAI"))
initial_eth = float(config_object.get("Initial Uniswap pool", "INITIAL_POOL_ETH"))

#Choice of distributions to draw agents from

#Agents have ETH holdings uniformly distributed between 1 and 50 ETH
distribution_eth = config_object.get("Agents parameters", "ETH_HOLDINGS_DISTRIBUTION")
parameter1_eth = float(config_object.get("Agents parameters", "LOWER_BOUND_ETH_HOLDINGS"))
parameter2_eth = float(config_object.get("Agents parameters", "UPPER_BOUND_ETH_HOLDINGS"))
eth_holdings_distribution = [distribution_eth, [parameter1_eth, parameter2_eth]]

#Agents who care about APY have a threshold of satisfactory APY between 10 and 400%

distribution_apy = config_object.get("Agents parameters", "APY_THRESHOLD_BUYANDSELL_APES_DISTRIBUTION")
parameter1_apy = float(config_object.get("Agents parameters", "APY_THRESHOLD_BUYANDSELL_APES_LOWER_BOUND"))
parameter2_apy = float(config_object.get("Agents parameters", "APY_THRESHOLD_BUYANDSELL_APES_UPPER_BOUND"))
apy_threshold_distribution = [distribution_apy, [parameter1_apy, parameter2_apy]]

#Agents have expected FLX total valuation uniformly distributed
distribution_flx = config_object.get("Agents parameters", "EXCEPTED_FLX_VALUATION_DISTRIBUTION")
parameter1_flx = float(config_object.get("Agents parameters", "LOWER_BOUND_FLX_VALUATION"))
parameter2_flx = float(config_object.get("Agents parameters", "UPPER_BOUND_FLX_VALUATION"))
expected_flx_valuation_distribution = [distribution_flx, [parameter1_flx,parameter2_flx]]

#Choice of the parameters of the RAI system 

#Choice of a controller and its parameters, in this case proportional with Kp = 0.01
controller_type = config_object.get("RAI system parameters", "CONTROLLER")
controller_parameter1 = float(config_object.get("RAI system parameters", "KP"))
controller_parameters = []
controller_parameters.append(controller_parameter1)
controller = [controller_type, controller_parameters]
#Initial redemption price of RAI in USD
initial_redemption_price = 3.14

#Initialize Uniswap pool with some arbitrary amount of liquidity
Pool = uniswap.UniswapPool(initial_rai, initial_eth)

#Initialize RAI system
System = rai_system.RAISystem(controller, initial_redemption_price, ETH_USD_PRICE)

#Initialize list of agents
Agents = [agents.BuyAndSellApe(eth_holdings_distribution, apy_threshold_distribution, expected_flx_valuation_distribution) for i in range(N_AGENTS)]

#Lists to plot at the end
twap_plot = []
redemption_rate_hourly_plot = []
redemption_price_hourly_plot = []

#Run the simulation

percentage_counter = 0
for i in range(N_HOURS):
    #Add the beginning of each hour period, add the current TWAP, redemption price, redemption rates to add to the lists to be plotted
    #Get the current TWAP IN USD
    twap_in_eth = Pool.getTWAP()
    twap_in_usd = ETH_USD_PRICE*Pool.getTWAP()
    redemption_price = System.redemption_price
    redemption_rate_hourly = System.redemption_rate_hourly
    #Convert hourly redemption rate from RAI.h-1 to %.h-1 (% of redemption price)
    redemption_rate_hourly_percent = (redemption_rate_hourly/redemption_price)*100
    twap_plot.append(twap_in_usd)
    redemption_rate_hourly_plot.append(redemption_rate_hourly_percent)
    redemption_price_hourly_plot.append(redemption_price)
    #Update the redemption price
    System.updateRedemptionPriceHourly()
    #Shuffle the agents: this makes the simulation non-deterministic 
    random.shuffle(Agents)
    for agent in Agents: 
        #Each agent sees if they want to do something 
        if agent.isAPYGood(Pool, System, FLX_PER_DAY_LIQUIDITY_PROVIDERS, ETH_USD_PRICE): 
        #If the APY is good and the agent doesn't have liquidity tokens, buy and liquidity. If they already have LP tokens, do nothing.
            if agent.wallet["lp tokens"] == 0:
                agent.buyAndProvide(Pool)
        #If the APY is not good, and the agent has liquidity tokens, remove liquidity and sell. If they don't have LP tokens, do nothing.
        else: 
            #print("Hey, I don't like this APY! \n")
            spot_price = Pool.getSpotPrice()
            if agent.wallet["lp tokens"] != 0:
                agent.removeAndSell(Pool)
                spot_price = Pool.getSpotPrice()
                #DEBUG
                x = 0

    #Get the price after agents have done all of their hourly interactions
    spot_price_in_eth = Pool.getSpotPrice()
    spot_price_in_usd = spot_price_in_eth*ETH_USD_PRICE
    #Update the redemption rate based on the TWAP at the end of this 1-hour period
    System.updateRedemptionRateHourly(twap_in_eth, ETH_USD_PRICE) 
    #Add the spot price IN ETH to the list containing the 16 previous end of hour spot prices
    Pool.addHourlyPrice(spot_price_in_eth)
    if i % 1740 == 0:
        print("Simulation running - ", percentage_counter, "%")
        percentage_counter += 20

#Plot results
days = [round(hour/24) for hour in range(N_HOURS)]
time_string = datetime.now().strftime('%Y-%m-%d %H-%M-%S')
plt.plot(days, twap_plot[0:len(twap_plot)], label = "TWAP")
plt.plot(days, redemption_price_hourly_plot[0:len(redemption_price_hourly_plot)], label = "Redemption price")
plt.legend(loc="lower left")
plt.xlabel("Days elapsed")
plt.ylabel("USD")
if not os.path.exists('results'):
    os.makedirs('results')
filename = 'price-evol '+time_string+'.png'
plt.savefig('results/'+filename)
#plt.show()
plt.close()

plt.plot(days, redemption_rate_hourly_plot[0:len(redemption_price_hourly_plot)])
plt.xlabel("Days elapsed")
plt.ylabel("Hourly redemption rate in %")
filename = 'redemption-rate-evol '+time_string+'.png'
plt.savefig('results/'+filename)
#plt.show()
plt.close()