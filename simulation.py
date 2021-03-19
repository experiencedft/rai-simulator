from configparser import ConfigParser

import rai_system
import agents
import uniswap

import random 
import time
from datetime import datetime
import os

import matplotlib.pyplot as plt 
import numpy as np

random.seed(int(time.time()))

#Import config
config_object = ConfigParser()
config_object.read("config.ini")

#Number of agents to interact with the system and the proportions of each agents
N_AGENTS = int(config_object.get("Global parameters", "N_AGENTS"))

ETH_USD_PRICE = float(config_object.get("Global parameters", "ETH_USD_PRICE"))
N_DAYS = int(config_object.get("Global parameters", "N_DAYS"))
N_HOURS = N_DAYS*24
FLX_PER_DAY_LIQUIDITY_PROVIDERS = float(config_object.get("Global parameters", "FLX_PER_DAY_LIQUIDITY_PROVIDERS"))

initial_rai = float(config_object.get("Initial Uniswap pool", "INITIAL_POOL_RAI"))
initial_eth = float(config_object.get("Initial Uniswap pool", "INITIAL_POOL_ETH"))

#Agents parameters

#Proportion of each type of agent to use in the simulation
BUY_AND_SELL_APES_PROPORTION = int(config_object.get("General agents parameters", "BUY_AND_SELL_APES_PROPORTION"))/100
SHORTERS_PROPORTION = int(config_object.get("General agents parameters", "SHORTERS_PROPORTION"))/100
assert BUY_AND_SELL_APES_PROPORTION + SHORTERS_PROPORTION == 1

#Buy and sell apes secific parameters

#Agents have ETH holdings uniformly distributed between 1 and 50 ETH
distribution_eth = config_object.get("Buy and sell apes parameters", "ETH_HOLDINGS_DISTRIBUTION")
parameter1_eth = float(config_object.get("Buy and sell apes parameters", "LOWER_BOUND_ETH_HOLDINGS"))
parameter2_eth = float(config_object.get("Buy and sell apes parameters", "UPPER_BOUND_ETH_HOLDINGS"))
eth_holdings_distribution_apes = [distribution_eth, [parameter1_eth, parameter2_eth]]

#Agents who care about APY have a threshold of satisfactory APY between 10 and 400%

distribution_apy = config_object.get("Buy and sell apes parameters", "APY_THRESHOLD_BUYANDSELL_APES_DISTRIBUTION")
parameter1_apy = float(config_object.get("Buy and sell apes parameters", "APY_THRESHOLD_BUYANDSELL_APES_LOWER_BOUND"))
parameter2_apy = float(config_object.get("Buy and sell apes parameters", "APY_THRESHOLD_BUYANDSELL_APES_UPPER_BOUND"))
apy_threshold_distribution = [distribution_apy, [parameter1_apy, parameter2_apy]]

#Agents have expected FLX total valuation uniformly distributed
distribution_flx = config_object.get("Buy and sell apes parameters", "EXCEPTED_FLX_VALUATION_DISTRIBUTION")
parameter1_flx = float(config_object.get("Buy and sell apes parameters", "LOWER_BOUND_FLX_VALUATION"))
parameter2_flx = float(config_object.get("Buy and sell apes parameters", "UPPER_BOUND_FLX_VALUATION"))
expected_flx_valuation_distribution = [distribution_flx, [parameter1_flx,parameter2_flx]]

#Shorters specific parameters

#Agents have ETH holdings uniformly distributed between 1 and 50 ETH
distribution_eth = config_object.get("Short RAI long ETH agents parameters", "ETH_HOLDINGS_DISTRIBUTION")
parameter1_eth = float(config_object.get("Short RAI long ETH agents parameters", "LOWER_BOUND_ETH_HOLDINGS"))
parameter2_eth = float(config_object.get("Short RAI long ETH agents parameters", "UPPER_BOUND_ETH_HOLDINGS"))
eth_holdings_distribution_shorters = [distribution_eth, [parameter1_eth, parameter2_eth]]

distribution_difference = config_object.get("Short RAI long ETH agents parameters", "DIFFERENCE_THRESHOLD_DISTRIBUTION")
parameter1_difference = float(config_object.get("Short RAI long ETH agents parameters", "DIFFERENCE_THRESHOLD_LOWER_BOUND"))
parameter2_difference = float(config_object.get("Short RAI long ETH agents parameters", "DIFFERENCE_THRESHOLD_UPPER_BOUND"))
difference_threshold_distribution = [distribution_difference, [parameter1_difference, parameter2_difference]]

distribution_stop_loss = config_object.get("Short RAI long ETH agents parameters", "STOP_LOSS_DISTRIBUTION")
parameter1_stop_loss = float(config_object.get("Short RAI long ETH agents parameters", "STOP_LOSS_LOWER_BOUND"))
parameter2_stop_loss = float(config_object.get("Short RAI long ETH agents parameters", "STOP_LOSS_UPPER_BOUND"))
stop_loss_distribution = [distribution_stop_loss, [parameter1_stop_loss, parameter2_stop_loss]]

distribution_collateralization = config_object.get("Short RAI long ETH agents parameters", "COLLATERALIZATION_DISTRIBUTION")
parameter1_collateralization = float(config_object.get("Short RAI long ETH agents parameters", "COLLATERALIZATION_LOWER_BOUND"))
parameter2_collateralization = float(config_object.get("Short RAI long ETH agents parameters", "COLLATERALIZATION_UPPER_BOUND"))
collateralization_distribution = [distribution_collateralization, [parameter1_collateralization, parameter2_collateralization]]

#Choice of the parameters of the RAI system 

#Choice of a controller and its parameters, in this case proportional with Kp = 0.01
Kp = float(config_object.get("RAI system parameters", "KP"))
Ki = float(config_object.get("RAI system parameters", "KI"))
Kd = float(config_object.get("RAI system parameters", "KD"))
controller_params = [Kp, Ki, Kd]

#Initial redemption price of RAI in USD
initial_redemption_price = ETH_USD_PRICE*(initial_eth/initial_rai)

#Initialize Uniswap pool with some arbitrary amount of liquidity
Pool = uniswap.UniswapPool(initial_rai, initial_eth)

#Initialize RAI system
System = rai_system.RAISystem(controller_params, initial_redemption_price, ETH_USD_PRICE)

#Initialize list of agents

#The types of agents to use in the simulation
agents_types_used = ["Buy and sell ape", "Shorter"]
#The respective proportions of each of these agents
agents_proportions = [BUY_AND_SELL_APES_PROPORTION, SHORTERS_PROPORTION]
#Draw agents types at random from requested proportions
agents_types_list = np.random.choice(agents_types_used, N_AGENTS, p=agents_proportions)

#Actually initialize the agents
Agents = []
for agent_type in agents_types_list:
    if agent_type == "Buy and sell ape":
        Agents.append(agents.BuyAndSellApe(eth_holdings_distribution_apes, apy_threshold_distribution, expected_flx_valuation_distribution))
    elif agent_type == "Shorter":
        Agents.append(agents.ShortRAI(eth_holdings_distribution_shorters, difference_threshold_distribution, stop_loss_distribution, collateralization_distribution))
    
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
    #Update the errors list of the system
    System.updateErrorsList(Pool, ETH_USD_PRICE)
    #Shuffle the agents: this makes the simulation non-deterministic 
    random.shuffle(Agents)
    for agent in Agents: 
        #Interaction flow for the apes
        if agent.type == "BuyAndSellApe":
            #Each agent sees if they want to do something 
            if agent.isAPYGood(Pool, System, FLX_PER_DAY_LIQUIDITY_PROVIDERS, ETH_USD_PRICE): 
            #If the APY is good and the agent doesn't have liquidity tokens, buy and liquidity. If they already have LP tokens, do nothing.
                if agent.wallet["lp tokens"] == 0:
                    agent.buyAndProvide(Pool)
            #If the APY is not good, and the agent has liquidity tokens, remove liquidity and sell. If they don't have LP tokens, do nothing.
            else: 
                spot_price = Pool.getSpotPrice()
                if agent.wallet["lp tokens"] != 0:
                    agent.removeAndSell(Pool)
                    spot_price = Pool.getSpotPrice()
        #Interaction flow for the long ETH short RAI agents
        elif agent.type == "ShortRAI":
            #If the agent has an active safe
            if agent.active_safes_counter == 0:
                #If the agent thinks the difference between market price and redemption price is high enough for them
                if agent.isDifferenceAboveThreshold(System, Pool, ETH_USD_PRICE):
                    #Mint RAI with half of the ETH in their wallet
                    agent.mint(System, Pool, agent.wallet["eth"]/2, ETH_USD_PRICE)
                    #Sell the RAI on the market
                    agent.sellRAI(Pool)
            #If the agent does not have any active safe
            else:
                if agent.isAbilityToRepayDebtCritical(System, Pool) or agent.isLossAboveStopLoss(System, Pool):
                    #Close the position
                    agent.buyAndRepay(System, Pool, ETH_USD_PRICE)
                elif agent.isSpotPriceBelowTarget(Pool, ETH_USD_PRICE) and all(rate > 0 for rate in redemption_rate_hourly_plot[-96:]):
                    agent.buyAndRepay(System, Pool, ETH_USD_PRICE)

    #Get the price after agents have done all of their hourly interactions
    spot_price_in_eth = Pool.getSpotPrice()
    spot_price_in_usd = spot_price_in_eth*ETH_USD_PRICE
    #Update the redemption rate based on the TWAP at the end of this 1-hour period - only after the second hour to let the derivative part of the controller act
    if i > 2:
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
plt.close()
# plt.show()

plt.plot(days, redemption_rate_hourly_plot[0:len(redemption_price_hourly_plot)])
plt.xlabel("Days elapsed")
plt.ylabel("Hourly redemption rate in %")
filename = 'redemption-rate-evol '+time_string+'.png'
plt.savefig('results/'+filename)
plt.close()
# plt.show()