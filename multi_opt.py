# Smart Charging in a single store with multiple packs/chargers
# Modeled as a CVXPY optimisation blending + scheduling problem
# Author: Sofia Taylor and Sotiris Gkoulimaris, Flexible Power Systems

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

branch = 457
vTypes = [['Arrival133', 'Arrival133']]
vNum = [[0, 16]]
chargers = [[22]]
batteries = [[1]]
run = 15
notes = 'Creating profiles for MO deck'
year = 2021

site_capacity_path = os.path.join(
    gv.INPUTS, '{}_meter_{}.csv'.format(branch, year))
capacity = pf.clean_site_capacityJLP(
    branch, year, site_capacity_path)
print('Capacity done')

print(capacity)

# Get list of dates from a set of journeys
t = "{}{}{}".format(branch, vTypes[0], chargers[0])
journeys = pickle.load(open(os.path.join(
    gv.JOURNEYS,
    "20-12.WEVC.Multi_Optimisation{}.pkl".format(t)), 'rb'))

print(journeys.describe())
alldates = pd.to_datetime(
    journeys['Start_Date_of_Route'].unique().astype(str))[50:55]

print(alldates)



# Get a price table
pricing_path = os.path.join(
    gv.INPUTS,
    "20-11.JLP.Time_Day_Rate_Workings.ST.01.xlsx")
price = pf.clean_JLpricing(pricing_path, alldates)

print(price)

for ch in chargers:
    print("How many chargers")
    for i, vs in enumerate(vTypes):
        run_dir = os.path.join(gv.LOGS, 'run{}'.format(run))
        jpath = os.path.join(gv.JOURNEYS,
                             "20-12.WEVC.Multi_Optimisation{}.pkl".format(t))
        #print(t, N, 'vehicles')
        journeysPri, vDict = pf.prep_data_mixed(jpath, vs, ch, alldates, vNum[i])

        vehicle_profs = pf.setup_inputs(journeysPri, price)

        site_capacity = {
            'opt': capacity['Available_kW'],
            'BAU': capacity['Available_nolim']
        }

        profile_out, dates, bad_days, lpprob, status, bats = (
            lpf.optimise_range(vehicle_profs,
                                ch, site_capacity, vDict, batteries))

        pd.to_pickle(profile_out, './pulp.plk')
        range_profile, site_profile, days_summary, global_summary = (
            of.summary_outputs(profile_out, journeys,
                               capacity['Available_kW'], status, vDict, bats))
        # Figures
        range_fig = of.daily_summary_plot(days_summary.fillna(0))
        range_fig.savefig(os.path.join(
            run_dir, 'fig_range{}.svg'.format(run)),
            bbox_inches="tight")
        plt.close(range_fig)

        heatplot = of.createHeatmap(
            site_profile, str(branch), [0, gv.STORE_SPEC[branch]['zMax']])
        heatplot.write_image(
            os.path.join(run_dir, 'heatplot{}.png'.format(run)),
            width=1800, height=1000)
        heatplot.write_html(
            os.path.join(run_dir, "heatplot{}.html".format(run)))


#print(vehicle_profs)

#print(vehicle_profs['Return'].describe())
