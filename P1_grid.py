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
run = 130
branch = 513
# Chargers to use in the grid, in kW
charger_power = [[11, 22], [7, 45]]  # [[11,11], [22,22], [7,22], [11,22]
caps = [60]  # 40, 120, 100, 150 300 100 200
grid_file_path = os.path.join(gv.LOGS1,
                              r'grid_search{}.csv'.format(run))
of.create_grid_file(grid_file_path)  # Creates a summary file
journeys = pf.prep_data(gv.data_path, gv.CATEGORY)
print('All journeys done')
journeys = pf.get_range_data(journeys, gv.DAY, gv.TIME_RANGE)
print('Range journeys done')
price_data = pf.clean_pricing(gv.pricing_path)
print('Prices done')
empty_profile = pf.create_empty_schedule(journeys, price_data)
print('Profiles done')

# journeys = pickle.load(open('Outputs/journeys_range','rb'))
# empty_profile = pickle.load(open('Outputs/empty_profile','rb'))

for charger in charger_power:
    for capacity in caps:
        script_strt = time.process_time()  # Capture start time
        run_dir = os.path.join(gv.LOGS1, 'run{}'.format(run))
        os.makedirs(os.path.join(run_dir,'daily'))
        print('Run:', run, '/ Charger:', charger, '/ Capacity:', capacity)
        site_capacity = {
            'opt': capacity,  # kWh (in a half-hour period so eq. 100 kW)
            'BAU': 10000,
            'BAU2': capacity
        }
        notes = """Test new changes"""
        profile_out, dates, bad_days, lpprob, status = lpf.optimise_range2(
            empty_profile,
            charger,
            site_capacity)

        range_profile, site_profile, days_summary, global_summary = of.summary_outputs(
        profile_out,
            journeys,
            capacity, status)

        ################ OUTPUTS ####################
        # Make and save daily figures
        for date in dates:
            day = dt.datetime.combine(date, dt.datetime.min.time())
            day_profile = of.create_daily_summary(site_profile, day)
            fig_summary = of.summary_plot(day_profile)
            fig_summary.savefig(os.path.join(
                run_dir, 'daily', 'fig{}.jpg'.format(date)))
            plt.close(fig_summary)
        #Scatter plot
        fig_scatter_outputs = of.scatter_plot(site_profile)
        fig_scatter_outputs.savefig(
            os.path.join(run_dir, 'opt_scatter{}.jpg'.format(run)),
            bbox_inches = "tight")
        plt.close(fig_scatter_outputs)

        range_fig = of.daily_summary_plot(days_summary.fillna(0))
        range_fig.savefig(
            os.path.join(run_dir, 'fig_range{}.svg'.format(run)),
            bbox_inches = "tight")
        plt.close(range_fig)

        heatplot = of.createHeatmap(site_profile)
        heatplot.write_image(
            os.path.join(run_dir, 'heatplot{}.png'.format(run)),
            width=1800, height=1000)
        heatplot.write_html(
            os.path.join(run_dir, "heatplot{}.html".format(run)))

        # Create a list of settings
        of.create_settings_file(run, run_dir, notes, charger, capacity,
                                branch, global_summary, bad_days)

        # Write problem to an .lp file
        lpprob['opt'].writeLP(os.path.join(
            run_dir, "multi_vehicle.lp"))

        # Save dataframes
        pickle.dump(range_profile,open(
            os.path.join(run_dir, 'range_profiles'), 'wb'))
        pickle.dump(site_profile,open(
            os.path.join(run_dir, 'site_summary'), 'wb'))
        pickle.dump(days_summary,open(
            os.path.join(run_dir, 'days_summary'),'wb'))
        pickle.dump(status,open(
            os.path.join(run_dir, 'status'),'wb'))
        runtime = time.process_time() - script_strt
        print('Range:', gv.TIME_RANGE, 'Time:',time.process_time(),'Runtime:',runtime)

        of.write_grid_file(grid_file_path, run, branch, charger, capacity,
                           runtime, global_summary, notes)
        run += 1


