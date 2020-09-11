# First approach to Smart Charging Phase 1 using PuLP.
# Modeled as a PuLP optimisation blending problem
# Started 20 Aug 2020
# Author: Sofia Taylor, Flexible Power Systems
# test new laptop

import numpy as np
import pandas as pd
import datetime as dt
from pulp import *
import pickle
import global_variables as gv
import functions as f
import matplotlib.pyplot as plt

run = 1# For now change this manually
notes = 'Initial log test'

# Import journey and price data

prot_journeys = pickle.load(open('Data/prototype_week','rb'))
test_journeys = pickle.load(open('Data/test_week','rb'))
BAU_profile = pickle.load(open('Data/BAU_profile','rb'))
day_journeys = f.get_daily_data(prot_journeys, gv.DAY)
day_profile = f.create_daily_schedule(BAU_profile, gv.DAY)

# Define output variable
outputs = LpVariable.dicts("output",
((period, vehicle) for period, vehicle in day_profile.index),
lowBound = 0,
upBound = 3.5,
cat = "Continuous"
)

# Create the 'prob' variable to contain the problem data
prob = LpProblem("Multiple_vehicle_scheduling",LpMinimize)

# Add costs to objective function

prob += lpSum(
    [day_profile.loc[(period, vehicle), 'unit_rate_excl_vat'] * outputs[period, vehicle] for period, vehicle in day_profile.index]
    ), "Total Charging costs"

# Final SOC constraint
time_period = day_profile.index.get_level_values(0)
vehicles = day_journeys.index

for vehicle in vehicles:
    prob += lpSum(
        [outputs[period, vehicle] for period in time_period])/gv.NUM_VEHICLES == day_journeys.loc[vehicle, 'Energy_Required'] / gv.CHARGER_EFF

# Output after/before departure/arrival is 0

for period, vehicle in day_profile.index:
    arrival = day_journeys.loc[vehicle, "End_Time_of_Route"]
    departure = day_journeys.loc[vehicle, "Start_next_route"]
    if period < arrival:
        prob += outputs[(period, vehicle)] == 0
    elif period + dt.timedelta(minutes=30) > departure:
        prob += outputs[period, vehicle] == 0

# Max capacity constraint
for period in time_period:
    prob += lpSum(
        [outputs[period, vehicle] for vehicle in vehicles]) <= gv.SITE_CAPACITY

# Solve and print to the screen
prob.solve()
print("Status:", LpStatus[prob.status])

# Get output variables
charge_output = []

for period, vehicle in outputs:
    var_output = {
        'from': period,
        'Vehicle': vehicle,
        'Output_Opt': outputs[(period, vehicle)].varValue
    }
    charge_output.append(var_output)

output_df = pd.DataFrame.from_records(charge_output).sort_values(['from','Vehicle'])
output_df.set_index(['from', 'Vehicle'], inplace=True)
print('Cost:', value(prob.objective))
day_profile = day_profile.merge(
    output_df,
    how='left',
    left_index=True,
    right_index=True,
    )

day_profile, day_journeys, site_summary, global_summary = f.summary_outputs(
    day_profile,
    day_journeys
)

fig, axs = plt.subplots(3,2,figsize=(10,15), sharex=True, gridspec_kw={'hspace':0.1})

x = day_profile.unstack().index.strftime('%H:%M')

axs[0,0].plot(x, day_profile['Output_Opt'].unstack())
axs[0,0].set_title('Optimiser profile per vehicle')

axs[0,1].plot(x, day_profile['Output_BAU'].unstack())
axs[0,1].set_title('BAU profile per vehicle')
axs[0,1].legend(vehicles)

axs[1,0].plot(x, day_profile['SOC_Opt'].unstack())
axs[1,0].set_title('Optimiser SOC per vehicle')

axs[1,1].plot(x, day_profile['SOC_BAU'].unstack())
axs[1,1].set_title('BAU SOC per vehicle')

axs[2,0].plot(x, site_summary['unit_rate_excl_vat'], label = 'Electricity price', color='tab:orange')
axs[2,0].plot(x, site_summary['Output_Opt'], label='Optimiser', color='tab:blue')
axs[2,0].plot(x, day_profile['Output_BAU'].groupby(level=0).sum(), label='BAU', color='tab:green')
axs[2,0].legend()
axs[2,0].set_title('Total site output')

axs[2,1].plot(x, site_summary['SOC_Opt'], label='SOC all vehicles',color='tab:blue')
axs[2,1].plot(x, site_summary['SOC_BAU'], label='SOC all vehicles BAU',color='tab:green')
axs[2,1].set_title('Total site SOC')

for ax in fig.get_axes():
    ax.xaxis.set_major_locator(plt.MaxNLocator(10))

# Create a list of settings
with open('global_variables.py','r') as f:
    global_variables = f.read()
os.makedirs('Outputs/Logs/run{}'.format(run))
with open('Outputs/Logs/run{}/variables{}.csv'.format(run,run),'a') as f:
    f.write(global_summary.to_string())
    f.write('\nglobal_variabes.py:\n')
    f.write(global_variables)
    f.write(notes)

# The problem data is written to an .lp file
prob.writeLP("Outputs/Logs/run{}/multi_vehicle.lp".format(run))

# Save dataframes
day_profile.to_json(r'Outputs/Logs/run{}/profiles{}.json'.format(run,run))
day_journeys.to_json(r'Outputs/Logs/run{}/vehicles{}.json'.format(run,run))
site_summary.to_json(r'Outputs/Logs/run{}/site_summary{}.json'.format(run,run))

# Save figure
fig.savefig('Outputs/Logs/run{}/fig{}.svg'.format(run,run),facecolog='white')
plt.close(fig)

