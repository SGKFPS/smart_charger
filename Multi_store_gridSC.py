# Smart Charging in multiple stores
# Modeled as a PuLP optimisation blending + scheduling problem
# Branched from P1_grid on 23/10/2020
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

run = 22
notes = 'New time of day "break" at 8am'

# jour = pf.prep_data_JLP(gv.multi_journey_path)
# pickle.dump(jour, open('Outputs/LogsJLP/all_journeys', 'wb'))
# print('All journeys done')

# price_data = pf.BAU_pricing(jour)
# pickle.dump(price_data, open('Outputs/LogsJLP/price_data', 'wb'))
# print('Prices done')

# empty_profs = {}
# for branch in gv.STORE_SPEC.keys():
#     journeys = jour[branch]
#     # journeys = pf.get_range_data(jour[branch], gv.DAY, gv.TIME_RANGE)
#     empty_profs[branch] = pf.create_empty_schedule(
#         journeys, price_data)
#     print('Profiles done for {}'.format(branch))
# pickle.dump(empty_profs,
#             open(os.path.join(gv.LOGS, r'empty_profiles'), 'wb'))

empty_profs = pickle.load(
    open(os.path.join(gv.LOGS, r'empty_profiles'), 'rb'))
jour = pickle.load(
    open(os.path.join(gv.LOGS, r'all_journeys'), 'rb'))

# Initialise grid search file
grid_file_path = os.path.join(gv.LOGS,
                              r'JLPbranches{}.csv'.format(run))
of.create_grid_file(grid_file_path)

for branch in gv.STORE_SPEC.keys():
    script_strt = time.process_time()
    run_dir = os.path.join(gv.LOGS, 'run{}'.format(run))
    os.makedirs(os.path.join(run_dir,'daily'))
    site_capacity = {
        'BAU': 10000}
    charger = gv.STORE_SPEC[branch]['CH']
    print('Run:', run,'/ Branch:', branch,
          '/ Charger:', charger, '/ Capacity:', 'All')
    veh = gv.STORE_SPEC[branch]['V']
    profile_out, dates, bad_days, lpprob, status = (
        lpf.optimise_range2(empty_profs[branch],
                            charger,
                            site_capacity, veh))

    range_profile, site_profile, days_summary, global_summary = (
        of.summary_outputs(profile_out,
                           jour[branch], 10000, status, veh))
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
    fig_scatter_outputs.savefig(os.path.join(
        run_dir, 'opt_scatter{}.jpg'.format(run)),
        bbox_inches = "tight")
    plt.close(fig_scatter_outputs)

    range_fig = of.daily_summary_plot(days_summary.fillna(0))
    range_fig.savefig(os.path.join(
        run_dir, 'fig_range{}.svg'.format(run)),
        bbox_inches = "tight")
    plt.close(range_fig)

    heatplot = of.createHeatmap(site_profile)
    heatplot.write_image(
        os.path.join(run_dir, 'heatplot{}.png'.format(run)),
        width=1800, height=1000)
    heatplot.write_html(
        os.path.join(run_dir, "heatplot{}.html".format(run)))

    # Write problem to an .lp file
    lpprob[gv.CATS[0]].writeLP(os.path.join(
        run_dir, "multi_vehicle.lp"))

    # Create a file with notes, settings and results
    of.create_settings_file(run, run_dir, notes, charger, 10000,
                            branch, global_summary, bad_days)
    # Save dataframes
    pickle.dump(range_profile,
                open(os.path.join(run_dir, 'range_profiles'), 'wb'))
    pickle.dump(site_profile,
                open(os.path.join(run_dir, 'site_summary'), 'wb'))
    pickle.dump(days_summary,
                open(os.path.join(run_dir, 'days_summary'), 'wb'))
    pickle.dump(status,
                open(os.path.join(run_dir, 'status'), 'wb'))
    runtime = time.process_time() - script_strt
    print('Range:', gv.TIME_RANGE, 'Runtime:',runtime)

    of.write_grid_file(grid_file_path, run, branch, charger, 10000,
                       runtime, global_summary, notes)
    run += 1