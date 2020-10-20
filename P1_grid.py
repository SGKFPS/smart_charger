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
import lin_prog_functions as lpf
import output_functions as of
import testdata_proc as pf
import matplotlib.pyplot as plt
import glob
import time
import random
import os

# Variables for grid search
run = 113
charger_power = [11,11], [22,22]]  # [[11,22],[7,22]], 45, 11, 7] # kW
caps = [40,60,120]#,500] #100 300 100 200
grid_file_path = 'Outputs/Logs/grid_variables{}.csv'.format(run)

journeys = pf.prep_data(gv.data_path, gv.CATEGORY)
print('All journeys done')
journeys = pf.get_range_data(all_journeys, gv.DAY, gv.TIME_RANGE)
print('Range journeys done')
price_data = pf.clean_pricing(gv.pricing_path)
print('Prices done')
empty_profile = pf.create_empty_schedule(journeys, price_data)
print('Profiles done')

# journeys = pickle.load(open('Outputs/journeys_range','rb'))
# empty_profile = pickle.load(open('Outputs/empty_profile','rb'))

for charger in charger_power:
    for capacity in caps:
        script_strt = time.process_time()
        print('Run:',run,'/ Charger:',charger,'/ Capacity:',capacity)
        site_capacity = {
            'opt': capacity,  # kWh (in a half-hour period so eq. 100 kW)
            'BAU': 10000,
            'BAU2': capacity
        }
        notes = """Grid search with mix of chargers"""
        os.makedirs('Outputs/Logs/run{}'.format(run))
        grid_file = open(grid_file_path,'a')
        grid_file.write('\n' + str(run)+'\n'+str(charger) + '\n' + str(capacity) +'\n')
        profile_out, dates, bad_days, lpprob, status = lpf.optimise_range2(
            empty_profile,
            charger,
            site_capacity)

        range_profile, site_profile, days_summary, global_summary = of.summary_outputs(
        profile_out,
            journeys,
            capacity)

        ################ OUTPUTS ####################
        # Make and save daily figures
        os.makedirs('Outputs/Logs/run{}/daily'.format(run))
        for date in dates:
            day = dt.datetime.combine(date, dt.datetime.min.time())
            day_profile = of.create_daily_summary(site_profile, day)
            fig_summary = of.summary_plot(day_profile)
            fig_summary.savefig(
                'Outputs/Logs/run{}/daily/fig{}.jpg'.format(run,date))
            plt.close(fig_summary)
        #Scatter plot
        fig_scatter_outputs = of.scatter_plot(site_profile)
        fig_scatter_outputs.savefig(
            'Outputs/Logs/run{}/opt_scatter{}.jpg'.format(run,run),
            bbox_inches = "tight")
        plt.close(fig_scatter_outputs)

        range_fig = of.daily_summary_plot(days_summary.fillna(0))
        range_fig.savefig(
            'Outputs/Logs/run{}/fig_range{}.svg'.format(run,run),
            bbox_inches = "tight")
        plt.close(range_fig)


        # Create a list of settings
        with open('global_variables.py','r') as f:
            global_variables = f.read()

        with open('Outputs/Logs/run{}/variables{}.csv'.format(run,run),'a') as fi:
            fi.write(notes)
            fi.write('\n' + str(run)+'\n'+str(charger) + '\n' + str(capacity) +'\n')
            fi.write(global_summary.to_string())
            fi.write(bad_days)
            fi.write('\n \n global_variables.py:\n')
            fi.write(global_variables)

        # Write problem to an .lp file
        lpprob['opt'].writeLP("Outputs/Logs/run{}/multi_vehicle.lp".format(run))

        # Save dataframes
        pickle.dump(range_profile,open('Outputs/Logs/run{}/range_profiles{}'.format(run,run),'wb'))
        pickle.dump(site_profile,open('Outputs/Logs/run{}/site_summary{}'.format(run,run),'wb'))
        pickle.dump(days_summary,open('Outputs/Logs/run{}/days_summary'.format(run),'wb'))
        pickle.dump(status,open('Outputs/Logs/run{}/status'.format(run),'wb'))
        grid_file.write(global_summary.to_string())
        grid_file.write('\n'+bad_days)
        runtime = time.process_time() - script_strt
        grid_file.write('\n'+str(runtime))
        print('Range:', gv.TIME_RANGE, 'Time:',time.process_time(),'Runtime:',runtime)
        run += 1
        grid_file.close()

