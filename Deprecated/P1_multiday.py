# Smart Charging P1 with a time range
# Modeled as a PuLP optimisation blending + scheduling problem
# Started 16/09/2020
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

# Variables for grid search
run = 28
charger_power = 22 # kW
site_capacity = {
    'opt': 50,  # kWh (in a half-hour period so eq. 100 kW)
    'BAU': 10000,
    'BAU2': 50
 }

notes = 'Grid test'
os.makedirs('Outputs/Logs/run{}'.format(run))

# Import journey and price data
script_strt = time.process_time()
journeys = pickle.load(open('Outputs/journeys_range','rb'))
empty_profile = pickle.load(open('Outputs/empty_profile','rb'))

profile_out, dates, bad_days, lpprob = lpf.optimise_range(
    journeys, 
    empty_profile, 
    charger_power, 
    site_capacity)

range_profile, range_journeys, veh_profile, site_profile, days_summary, global_summary = of.summary_outputs(
   profile_out, 
    journeys, 
    dates)

print(global_summary)

################ OUTPUTS ####################

# Make and save daily figures
os.makedirs('Outputs/Logs/run{}/daily'.format(run))
for date in dates:
    day = dt.datetime.combine(date, dt.datetime.min.time())
    day_profile = of.create_daily_summary(site_profile, day)
    fig_summary = of.summary_plot(day_profile)
    fig_summary.savefig(
        'Outputs/Logs/run{}/daily/fig{}.svg'.format(run,date))
    plt.close(fig_summary)

range_fig = of.daily_summary_plot(days_summary)
range_fig.savefig(
    'Outputs/Logs/run{}/fig_range{}.svg'.format(run,run),
    bbox_inches = "tight")
plt.close(range_fig)

 
# Create a list of settings
with open('global_variables.py','r') as f:
    global_variables = f.read()

with open('Outputs/Logs/run{}/variables{}.csv'.format(run,run),'a') as fi:
    fi.write(global_summary.to_string())
    fi.write('\nglobal_variabes.py:\n')
    fi.write(global_variables)
    fi.write(notes)
    fi.write(bad_days)

# Write problem to an .lp file
lpprob['opt'].writeLP("Outputs/Logs/run{}/multi_vehicle.lp".format(run))

# Save dataframes
pickle.dump(range_profile,open('Outputs/Logs/run{}/route_profiles{}'.format(run,run),'wb'))
pickle.dump(veh_profile,open('Outputs/Logs/run{}/veh_profiles{}'.format(run,run),'wb'))
pickle.dump(range_journeys,open('Outputs/Logs/run{}/journeys{}'.format(run,run),'wb'))
pickle.dump(site_profile,open('Outputs/Logs/run{}/site_summary{}'.format(run,run),'wb'))
pickle.dump(days_summary,open('Outputs/Logs/run{}/days_summary'.format(run),'wb'))

print('Time:', gv.TIME_RANGE, time.process_time() - script_strt)