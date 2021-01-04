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
import time
import os

branch = 513

vTypes = [['Arrival111', 'Arrival111']]
# vNum = [[0, 116]]
chargers = [[11, 22]]
# # vTypes = [['Arrival111', 'Arrival111'],
# #           ['Arrival67', 'Arrival111'], ['Arrival44', 'Arrival111']]
vNum = [[0, 116]]


run = 93
notes = 'Creating profiles for MO deck'
year = 2021

# Get site capacity
capacity = pf.clean_site_capacityJLP(
    branch, year, 'Inputs/{}_meter_{}.csv'.format(branch, year))
print('Capacity done for {}'.format(branch))

# Get list of dates
t = "{}{}{}".format(branch, vTypes[0], '[22]')  # chargers[0]########################################################
# journeys = pickle.load(open(
#     "C:/Users/SofiaTaylor/OneDrive - Flexible Power Systems Ltd/"
#     "dev/Journey_analysis/JLP2/Outputs/MultiOptimisation/{}_synth2021/"
#     "20-12.WEVC.Multi_Baseline457['Arrival133'][60].pkl".format(branch), 'rb'))
journeys = pickle.load(open(
    "C:/Users/SofiaTaylor/OneDrive - Flexible Power Systems Ltd/"
    "dev/Journey_analysis/JLP2/Outputs/MultiOptimisation/{}_synth2021/"
    "20-12.WEVC.Multi_Optimisation{}.pkl".format(branch, t), 'rb'))
alldates = pd.to_datetime(journeys['Start_Date_of_Route'].unique().astype(str))[50:55]
price = pf.clean_JLpricing(gv.JLP_pricing_path, alldates)

# Initialise grid search file
grid_file_path = os.path.join(gv.LOGS2,
                              r'JLPmixed{}.csv'.format(run))
of.create_grid_file(grid_file_path)

for ch in chargers:
    for i, vs in enumerate(vTypes):
        script_strt = time.process_time()
        run_dir = os.path.join(gv.LOGS2, 'run{}'.format(run))
        os.makedirs(os.path.join(run_dir,'daily'))
        t = "{}{}{}".format(branch, vs, '[22]')  # ch ###################################################################
        N = sum(vNum[i])
        jpath = (
            "C:/Users/SofiaTaylor/OneDrive - Flexible Power Systems Ltd/"
            "dev/Journey_analysis/JLP2/Outputs/MultiOptimisation/{}_synth2021/"
            "20-12.WEVC.Multi_Optimisation{}.pkl".format(branch, t))
        print(t, N, 'vehicles')
        journeys, vDict = pf.prep_data_mixed(jpath, vs, ch, alldates, vNum[i])
        pickle.dump(journeys,
                    open(os.path.join(run_dir, 'journeys.pkl'), 'wb'))
        empty_profs = pf.create_empty_schedule(journeys, price)
        # empty_profs = pickle.load(open(
        #     "Outputs/LogsMixed/empty_profs{}.pkl".format(t), 'rb'))
        pickle.dump(empty_profs,
                    open(os.path.join(run_dir, 'empty_profs{}.pkl'.format(t)), 'wb'))
        print('Profiles done for {}'.format(branch))
        site_capacity = {
            'opt': capacity['Available_kW'],
            'BAU': capacity['Available_nolim']
        }
        profile_out, dates, bad_days, lpprob, status = (
            lpf.optimise_range3(empty_profs,
                                ch, site_capacity, vDict))
        range_profile, site_profile, days_summary, global_summary = (
            of.summary_outputs(profile_out, journeys,
                               capacity['Available_kW'], status, vDict))
        ################ OUTPUTS ####################
        # Make and save daily figures
        # for date in dates:
        #     day = dt.datetime.combine(date, dt.datetime.min.time())
        #     day_profile = of.create_daily_summary(site_profile, day)
        #     fig_summary = of.summary_plot(day_profile)
        #     fig_summary.savefig(os.path.join(
        #         run_dir, 'daily', 'fig{}.jpg'.format(date)))
        #     plt.close(fig_summary)
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

        heatplot = of.createHeatmap(
            site_profile, str(branch), [0, gv.STORE_SPEC[branch]['zMax']])
        heatplot.write_image(
            os.path.join(run_dir, 'heatplot{}.png'.format(run)),
            width=1800, height=1000)
        heatplot.write_html(
            os.path.join(run_dir, "heatplot{}.html".format(run)))

        # Write problem to an .lp file
        lpprob[gv.CATS[0]].writeLP(os.path.join(
            run_dir, "multi_vehicle.lp"))

        # Create a file with notes, settings and results
        of.create_settings_file(run, run_dir, notes, ch, 10000,
                                branch, global_summary, bad_days, vDict)
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
        print('Branch:', branch, 'Runtime:', runtime)

        of.write_grid_file(
            grid_file_path, run, branch, ch, gv.STORE_SPEC[branch]['ASC'],
            runtime, global_summary, notes, vs, vNum[i])
        run += 1