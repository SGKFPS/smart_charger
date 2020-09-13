# First approach to Smart Charging Phase 1 using PuLP.
# Modeled as a PuLP optimisation blending + scheduling problem
# Started 10/9/2020
# Author: Sofia Taylor, Flexible Power Systems

import numpy as np
import pandas as pd
import datetime as dt
from pulp import *
import pickle
import global_variables as gv
import functions as f
import matplotlib.pyplot as plt
import glob
import timeit

import random

run = 3# For now change this manually
notes = 'Same as run 2, change to .py'

# Import journey and price data

journeys = pickle.load(open('Outputs/journeys_range','rb'))
#all_journeys = pickle.load(open('Outputs/all_journeys','rb'))
price_data = pickle.load(open('Outputs/price_data','rb'))
BAU_profile = f.BAU_charging(journeys, price_data)
day_journeys = f.get_daily_data(journeys, gv.DAY)
day_profile = f.create_daily_schedule(BAU_profile, gv.DAY)

def linear_optimiser(profile,journeys,ca):
    price_col = gv.CAT_COLS['PRICE'][ca]
    output_col = gv.CAT_COLS['OUTPUT'][ca]
    # Define output variable
    outputs = LpVariable.dicts("output",
    ((period, route) for period, route in profile.index),
    lowBound = 0,
    upBound = gv.CHARGER_POWER * gv.TIME_FRACT,
    cat = "Continuous"
    )

    # Create the 'prob' variable to contain the problem data
    prob = LpProblem("Multiple_route_scheduling",LpMinimize)

    # Add costs to objective function

    prob += lpSum(
        [profile.loc[(period, route), price_col] * outputs[period, route] for period, route in profile.index]
        ), "Total Charging costs"

    # Final SOC constraint
    time_period = profile.index.get_level_values(0)
    routes = profile.index.get_level_values(1)
    vehicles = journeys['Vehicle_ID'].unique()

    for vehicle in vehicles:
        vehicle_profile = profile[day_profile['Vehicle_ID'] == vehicle]
        prob += lpSum(
            [outputs[period, route] for period, route in vehicle_profile.index]) == journeys[journeys['Vehicle_ID'] == vehicle]['Energy_Required'].sum() / gv.CHARGER_EFF

    # Output after/before departure/arrival is 0

    for period, route in profile.index:
        arrival = journeys.loc[route, "End_Time_of_Route"]
        departure = journeys.loc[route, "Next_Departure"]
        if period < arrival:
            prob += outputs[(period, route)] == 0
        elif period + dt.timedelta(minutes=30) > departure:
            prob += outputs[period, route] == 0

    # Max capacity constraint
    n = len(time_period.unique())
    for period in time_period:
        prob += lpSum(
            [outputs[period, route] for route in routes])/n <= gv.SITE_CAPACITY[ca]
    
    # Solve and print to the screen
    prob.solve()
    print("Status:",ca, LpStatus[prob.status])

    # Get output variables
    charge_output = []

    for period, route in outputs:
        var_output = {
            'from': period,
            'Route_ID': route,
            output_col: outputs[(period, route)].varValue
        }
        charge_output.append(var_output)

    df = pd.DataFrame.from_records(charge_output).sort_values(['from','Route_ID'])
    df.set_index(['from', 'Route_ID'], inplace=True)
    print('Cost:', value(prob.objective))
    return df, prob

output_df = {}
PuLP_prob = {}
day_profile_out = day_profile.copy()
for ca in gv.CATS:
    output_df[ca], PuLP_prob[ca] = linear_optimiser(
        day_profile,
        day_journeys,
        ca
        )
    day_profile_out = day_profile_out.merge(
    output_df[ca],
    how='left',
    left_index=True,
    right_index=True,
    )

day_profile, day_journeys, site_summary, global_summary = f.summary_outputs(
    day_profile_out,
    day_journeys
)

fig, axs = plt.subplots(2,2,figsize=(15,15), sharex=True, gridspec_kw={'hspace':0.1})
routes = day_profile_out.index.get_level_values(1)
x = day_profile.unstack().index.strftime('%H:%M')
cats = gv.CATS
cols = gv.CAT_COLS


# axs[0,1].plot(x, day_profile_out[gv.CAT_COLS['OUTPUT']['BAU']].unstack())
# axs[0,1].set_title('BAU profile per Route')
# axs[0,1].legend(routes)

for ca in cats:
    axs[0,0].plot(x, site_summary[cols['NUM'][ca]], label=ca, color=gv.COLOR[ca])
    axs[0,1].plot(x, site_summary[cols['ECOST'][ca]], label=ca, color=gv.COLOR[ca])
    axs[1,0].plot(x, site_summary[cols['OUTPUT'][ca]], label=ca, color=gv.COLOR[ca])
    axs[1,1].plot(x, site_summary[cols['SOC'][ca]], label=ca, color=gv.COLOR[ca])

axs[1,0].legend()
axs[0,0].plot(x, site_summary[cols['PRICE']['opt']], label='Eletricity_price', color='tab:red')
axs[0,0].set_title('Number of Vehicles Charging')
axs[0,1].set_title('Electricity Costs')
axs[1,0].set_title('Total site output')
axs[1,1].set_title('Total site SOC')

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
for ca in gv.CATS:
    PuLP_prob[ca].writeLP("Outputs/Logs/run{}/multi_vehicle.lp".format(run))

# Save dataframes
day_profile.to_json(r'Outputs/Logs/run{}/profiles{}.json'.format(run,run))
day_journeys.to_json(r'Outputs/Logs/run{}/vehicles{}.json'.format(run,run))
site_summary.to_json(r'Outputs/Logs/run{}/site_summary{}.json'.format(run,run))

# Save figure
fig.savefig('Outputs/Logs/run{}/fig{}.svg'.format(run,run),facecolog='white')
plt.close(fig)