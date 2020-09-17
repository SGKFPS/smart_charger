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
import lin_prog_functions as lpf
import output_functions as of
import matplotlib.pyplot as plt
import glob
import time
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
    output_df[ca], PuLP_prob[ca] = lpf.linear_optimiser_V1(
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

day_profile, day_journeys, site_summary, global_summary = of.summary_outputs(
    day_profile_out,
    day_journeys
)

# Create all the outputs
os.makedirs('Outputs/Logs/run{}'.format(run))

# Make and save figures
fig_summary = of.summary_plot(site_summary)
fig_summary.savefig(
    'Outputs/Logs/run{}/fig{}.svg'.format(run,run))
fig_summary.savefig(
    'Outputs/Logs/run{}/fig{}.jpg'.format(run,run))
plt.close(fig_summary)

fig_BAU = of.summary_BAU_plot(site_summary)
fig_BAU.savefig(
    'Outputs/Logs/run{}/fig_BAU{}.svg'.format(run,run),
    bbox_inches = "tight")
plt.close(fig_BAU)

fig_scatter_outputs = of.scatter_plot(site_summary)
fig_scatter_outputs.savefig(
    'Outputs/Logs/run{}/opt_scatter{}.jpg'.format(run,run),
    bbox_inches = "tight")
plt.close(fig_scatter_outputs)

min_time = dt.datetime(2019,2,10,5,0,0)
max_time = dt.datetime(2019,2,10,23,30,0)
fig_journey_hist = of.histograms_journeys(day_journeys, min_time, max_time)
fig_journey_hist.savefig(
    'Outputs/Logs/run{}/journey_hist{}.jpg'.format(run,run),
    bbox_inches = "tight")
plt.close(fig_journey_hist)
 
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

########################
#To tidy json dataframes
# day_profile['Index'] = day_profile.index.values
# day_profile['from'] = day_profile['Index'].str.split('\'').str[1]
# day_profile['Route_ID'] = day_profile['Index'].str[-8:-1]
# day_profile['from'] = day_profile['from'].astype('datetime64[ns]')
# day_profile.drop(columns='Index',inplace=True)
# day_profile.set_index(['from','Route_ID'],inplace=True)

# site_summary['Index'] = site_summary.index.values
# site_summary['from'] = site_summary['Index'].astype('datetime64[ns]')
# site_summary.drop(columns='Index',inplace=True)
# site_summary.set_index(['from'],inplace=True)
# site_summary.head()

# # To set fonts
# font_dirs = ['Data\Source_Sans_Pro', ]
# font_files = font_manager.findSystemFonts(fontpaths=font_dirs)
# font_list = font_manager.createFontList(font_files)
# font_manager.fontManager.ttflist.extend(font_list)

# mpl.rcParams['font.family'] = 'Source Sans Pro'