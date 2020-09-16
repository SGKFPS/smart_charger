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
import time
import lin_prog as lp
import random
import os

run = 21# For now change this manually
notes = 'Playing with graphs'

# Import journey and price data

journeys = pickle.load(open('Outputs/journeys_range','rb'))
price_data = pickle.load(open('Outputs/price_data','rb'))
empty_profile = pickle.load(open('Outputs/empty_profile','rb'))
day_journeys = f.get_daily_data(journeys, gv.DAY)
day_profile = f.create_daily_schedule(empty_profile, gv.DAY)

output_df = {}
PuLP_prob = {}
day_profile_out = day_profile.copy()
for ca in gv.CATS:
    start = time.process_time()
    output_df[ca], PuLP_prob[ca] = lp.linear_optimiser_V1(
        day_profile,
        day_journeys,
        ca
        )
    print('Time:' , time.process_time() - start)
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

# Create all the outputs
os.makedirs('Outputs/Logs/run{}'.format(run))

fig = f.summary_plot(site_summary)
fig2 = f.summary_BAU_plot(site_summary)

# Save figures
fig.savefig('Outputs/Logs/run{}/fig{}.svg'.format(run,run),facecolog='white')
fig.savefig('Outputs/Logs/run{}/fig{}.jpg'.format(run,run),facecolog='white')
plt.close(fig)

fig2.savefig(
    'Outputs/Logs/run{}/fig_BAU{}.svg'.format(run,run),
    facecolog='white',
    bbox_inches = "tight"
    )
plt.close(fig2)

# Create a list of settings
with open('global_variables.py','r') as f:
    global_variables = f.read()

with open('Outputs/Logs/run{}/variables{}.csv'.format(run,run),'a') as f:
    f.write(global_summary.to_string())
    f.write('\nglobal_variabes.py:\n')
    f.write(global_variables)
    f.write(notes)

# Write problem to an .lp file
for ca in gv.CATS:
    PuLP_prob[ca].writeLP("Outputs/Logs/run{}/multi_vehicle.lp".format(run))

# Save dataframes
day_profile.to_json(r'Outputs/Logs/run{}/profiles{}.json'.format(run,run))
day_journeys.to_json(r'Outputs/Logs/run{}/vehicles{}.json'.format(run,run))
site_summary.to_json(r'Outputs/Logs/run{}/site_summary{}.json'.format(run,run))


# # Save scatter plot

# fig, axs = plt.subplots(1,
# figsize=(8,4))

# x = site_summary.groupby('Electricity_Price').mean().index
# y1 = site_summary.groupby('Electricity_Price').sum()
# cols=['Output_BAU','Output_BAU2','Output_Opt']
# y1[cols] = y1[cols].replace({0:np.nan})

# axs.scatter(x, y1['Output_Opt'],color=gv.COLOR['opt'],alpha=1,label='Smart Charging')
# axs.scatter(x, y1['Output_BAU'],color=gv.COLOR['BAU'],alpha=0.6,label='Unconstrained BAU')
# axs.scatter(x, y1['Output_BAU2'],color=gv.COLOR['BAU2'],alpha=0.6,label='Constrained BAU')

# axs.set_ylabel('Output (kWh)')
# axs.set_xlabel('Electricity Price (p / kWh)')
# axs.xaxis.set_major_locator(plt.MaxNLocator(10))
# axs.legend()
# fig.savefig('Outputs/Logs/run{}/opt_price{}.jpg'.format(run,run),facecolog='white',
# bbox_inches = "tight")

# # plot histograms
# min_time = dt.datetime(2019,2,10,5,0,0)
# max_time = dt.datetime(2019,2,10,23,30,0)
# bins_time = [min_time + i * dt.timedelta(minutes=30) for i in range (38)]

# fig, ax = plt.subplots(1,
# figsize=(6,2))
# ax.hist(day_journeys['Start_Time_of_Route'], 
# bins=bins_time,
# color=gv.FPS_BLUE,
# alpha=0.6,
# label='Departures')
# ax.hist(day_journeys['End_Time_of_Route'], 
# bins=bins_time,
# color=gv.FPS_GREEN,
# alpha=0.6,
# label='Arrivals')
# # locator = mdates.HourLocator()
# # ax.set_xlim([min_time,max_time])
# # ax.xaxis.set_major_locator(locator)
# ax.xaxis.set_major_formatter(mdates.DateFormatter('%H'))
# ax.legend(frameon=False)
# ax.set_xlabel('Time interval', color=gv.FPS_BLUE, fontweight='bold')
# ax.set_ylabel('# Vehicles', color=gv.FPS_BLUE, fontweight='bold')
# fig.savefig('Outputs/Logs/run{}/journeys{}.jpg'.format(run,run),facecolog='white',
# bbox_inches = "tight")
# plt.show()