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

run = 22# For now change this manually
notes = 'Multiday'

# Import journey and price data

journeys = pickle.load(open('Outputs/journeys_range','rb'))
price_data = pickle.load(open('Outputs/price_data','rb')) #TODO do I need this?
empty_profile = pickle.load(open('Outputs/empty_profile','rb'))
dates = np.unique(empty_profile.index.get_level_values(0).date)
dates = np.delete(dates,-1)
all_days_profile = []
dates_status = []
status = 0
i = 0
for date in dates:
    day_status = 0
    start = time.process_time()
    day = dt.datetime.combine(date, dt.datetime.min.time())
    day_journeys = f.get_daily_data(journeys, day)
    day_profile = f.create_daily_schedule(empty_profile, day)
    if len(day_profile)==0:
        print('Empty day',day)
        pass
    else:
        output_df = {}
        PuLP_prob = {}
        day_profile_out = day_profile.copy()
        for ca in gv.CATS:
            output_df[ca], PuLP_prob[ca] = lpf.linear_optimiser_V1(
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
            day_status += PuLP_prob[ca].status
        
        print(
            date,
            '\nTime:', time.process_time() - start,
            '\nStatus:',day_status, ':', PuLP_prob['opt'].status, PuLP_prob['BAU'].status,PuLP_prob['BAU2'].status,
            '\nCost:', value(PuLP_prob['opt'].objective))
        all_days_profile.append(day_profile_out)
        dates_status.append([date,day_status])

profile_out = pd.concat(all_days_profile)
print(profile_out.shape)
print(dates_status)

# day_profile, day_journeys, site_summary, global_summary = of.summary_outputs(
#     day_profile_out,
#     day_journeys
# )

# # Create all the outputs
# os.makedirs('Outputs/Logs/run{}'.format(run))

# # Make and save figures
# fig_summary = of.summary_plot(site_summary)
# fig_summary.savefig(
#     'Outputs/Logs/run{}/fig{}.svg'.format(run,run))
# fig_summary.savefig(
#     'Outputs/Logs/run{}/fig{}.jpg'.format(run,run))
# plt.close(fig_summary)

# fig_BAU = of.summary_BAU_plot(site_summary)
# fig_BAU.savefig(
#     'Outputs/Logs/run{}/fig_BAU{}.svg'.format(run,run),
#     bbox_inches = "tight")
# plt.close(fig_BAU)

# fig_scatter_outputs = of.scatter_plot(site_summary)
# fig_scatter_outputs.savefig(
#     'Outputs/Logs/run{}/opt_scatter{}.jpg'.format(run,run),
#     bbox_inches = "tight")
# plt.close(fig_scatter_outputs)

# min_time = dt.datetime(2019,2,10,5,0,0)
# max_time = dt.datetime(2019,2,10,23,30,0)
# fig_journey_hist = of.histograms_journeys(day_journeys, min_time, max_time)
# fig_journey_hist.savefig(
#     'Outputs/Logs/run{}/journey_hist{}.jpg'.format(run,run),
#     bbox_inches = "tight")
# plt.close(fig_journey_hist)
 
# # Create a list of settings
# with open('global_variables.py','r') as f:
#     global_variables = f.read()

# with open('Outputs/Logs/run{}/variables{}.csv'.format(run,run),'a') as f:
#     f.write(global_summary.to_string())
#     f.write('\nglobal_variabes.py:\n')
#     f.write(global_variables)
#     f.write(notes)

# # Write problem to an .lp file
# for ca in gv.CATS:
#     PuLP_prob[ca].writeLP("Outputs/Logs/run{}/multi_vehicle.lp".format(run))

# # Save dataframes
# day_profile.to_json(r'Outputs/Logs/run{}/profiles{}.json'.format(run,run))
# day_journeys.to_json(r'Outputs/Logs/run{}/vehicles{}.json'.format(run,run))
# site_summary.to_json(r'Outputs/Logs/run{}/site_summary{}.json'.format(run,run))