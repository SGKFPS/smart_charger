# First approach to Smart Charging Phase 1 using PuLP - single vehicle
# Modeled as a PuLP optimisation blending problem
# Started 20 Aug 2020
# Author: Sofia Taylor, Flexible Power Systems

import numpy as np
import pandas as pd
import datetime as dt
from pulp import *
import pickle
import global_variables as gv
import functions as f
import matplotlib.pyplot as plt

# Import journey and price data

prot_journeys = pickle.load(open('Data/prototype_week','rb'))
test_journeys = pickle.load(open('Data/test_week','rb'))
electricity_price = pickle.load(open('Data/price_data','rb'))
BAU_profile = pickle.load(open('Data/BAU_profile','rb'))

BAU_profile['Site_output'] = BAU_profile[gv.Power_output.values()].sum(axis=1)
BAU_profile['Electricity_costs'] = BAU_profile['Site_output'] * BAU_profile['unit_rate_excl_vat']

# Create plot of BAU model
plot = BAU_profile.plot(x='from', y='Site_output', kind='line')
fig = plot.get_figure()
fig.savefig('Data/BAU_profile_output.png')

# Creates a list of the time periods
start_datetime = BAU_profile.iloc[0,1]
end_datetime = start_datetime + dt.timedelta(days=1)
day_profile = BAU_profile[BAU_profile['from'] < end_datetime][['from','Output_1']]
day_profile = day_profile.merge(electricity_price[['from','unit_rate_excl_vat']], on='from')
time_periods = list(day_profile.index)

# Create a dictionary of price costs
prices = day_profile.unit_rate_excl_vat.to_dict()

# Get required charge for the day
day = dt.datetime(2020,2,10)
vehicle = 1
required_charge = prot_journeys.loc[(day, vehicle),'Required_SOC']

# Create the 'prob' variable to contain the problem data
prob = LpProblem("Single_vehicle_scheduling",LpMinimize)

# A dictionary called 'power_vars' is created to contain the referenced Variables
power_vars = LpVariable.dicts("Power",time_periods,0,3.5)

# The objective function is added to 'prob' first
prob += lpSum([prices[i]*power_vars[i] for i in time_periods]), "Total Charging costs"

# The constraints are added to 'prob'
prob += lpSum([power_vars[i] for i in time_periods]) == required_charge, "Required SOC"

# The problem data is written to an .lp file
prob.writeLP("Models/single_vehicle.lp")

# The problem is solved using PuLP's choice of Solver
prob.solve()

# The status of the solution is printed to the screen
print("Status:", LpStatus[prob.status])

# Each of the variables is printed with it's resolved optimum value
varsdict = {}
# for v in prob.variables():
#     print(v.name, "=", v.varValue)

for i in range(len(prob.variables())): #FIXME add to previous loop
    print(i,power_vars[i],power_vars[i].value())
    day_profile.loc[i,'Opt_output'] = power_vars[i].value()

# The optimised objective function value is printed to the screen
print("Total Cost of Electrivity = ", value(prob.objective))

fig, axs = plt.subplots(2)
x = day_profile['from'].dt.strftime('%H')
y = day_profile['Opt_output']
prices = day_profile['unit_rate_excl_vat']
axs[0].plot(x, y, label='Optimisation output')
axs[0].plot(x, day_profile['Output_1'], label='BAU output')
axs[1].plot(x, day_profile['unit_rate_excl_vat'], label = 'Electricity price')
axs[0].legend()
axs[1].legend()
fig.savefig('Data/singe_veh.jpg')
