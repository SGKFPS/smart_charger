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

# Variables for grid search
run = 68
charger_power = [22]#, 45, 11, 7] # kW
caps = [80]#,500] #100 300 100 200
grid_file_path = 'Outputs/Logs/grid_variables{}.csv'.format(run)
journeys = pickle.load(open('Outputs/journeys_range','rb'))
empty_profile = pickle.load(open('Outputs/empty_profile','rb'))

for charger in charger_power:
    for capacity in caps:
        script_strt = time.process_time()
        print('Run:',run,'/ Charger:',charger,'/ Capacity:',capacity)
        site_capacity = {
            'opt': capacity,  # kWh (in a half-hour period so eq. 100 kW)
            'BAU': 10000,
            'BAU2': capacity
        }
        notes = 'Test with SOC in optimisation'
        os.makedirs('Outputs/Logs/run{}'.format(run))
        grid_file = open(grid_file_path,'a')
        grid_file.write('\n' + str(run)+'\n'+str(charger) + '\n' + str(capacity) +'\n')
        profile_out, dates, bad_days, lpprob = lpf.optimise_range(
            empty_profile, 
            charger, 
            site_capacity)

        range_profile, site_profile, days_summary, global_summary = of.summary_outputs(
        profile_out, 
            journeys, 
            dates)

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
            # #BAU plot #FIXME
            # fig_BAU = of.summary_BAU_plot(day_profile)
            # fig_BAU.savefig(
            #     'Outputs/Logs/run{}/fig_BAU{}.svg'.format(run,run),
            #     bbox_inches = "tight")
            # plt.close(fig_BAU)
            # #Scatter plot #FIXME
            # fig_scatter_outputs = of.scatter_plot(day_profile)
            # fig_scatter_outputs.savefig(
            #     'Outputs/Logs/run{}/opt_scatter{}.jpg'.format(run,run),
            #     bbox_inches = "tight")
            # plt.close(fig_scatter_outputs)

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
            fi.write('\n \n global_variabes.py:\n')
            fi.write(global_variables)

        # Write problem to an .lp file
        lpprob['opt'].writeLP("Outputs/Logs/run{}/multi_vehicle.lp".format(run))

        # Save dataframes
        pickle.dump(range_profile,open('Outputs/Logs/run{}/route_profiles{}'.format(run,run),'wb'))
        pickle.dump(site_profile,open('Outputs/Logs/run{}/site_summary{}'.format(run,run),'wb'))
        pickle.dump(days_summary,open('Outputs/Logs/run{}/days_summary'.format(run),'wb'))
        grid_file.write(global_summary.to_string())
        grid_file.write('\n'+bad_days)
        runtime = time.process_time() - script_strt
        grid_file.write('\n'+str(runtime))
        print('Range:', gv.TIME_RANGE, 'Time:',time.process_time(),'Runtime:',runtime)
        run += 1
        grid_file.close()

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