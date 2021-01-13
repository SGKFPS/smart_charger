# Smart Charging Tool

This tool was developed to optimise the charging of a fleet of electric
vehicles according to various costs.

The current Phase 2 focuses on charging at low priced period while
maintining overall site below site capacity.
New features in this version:

* This phase incorporates real-world ASC and site loads
* Charge to next day's requirements (instead of 100%) or to breach site capacity if absolutely necessary.
* Uses a mix of chargers
* Uses a mix of vehicles

The optimisation is done using **PuLP**, a linear programming package.

This current version runs a smart charging algorithm for a given store for a given combination of journeys at a time. The main script is set up to iterate over different scenarios over the same time period and in the same store.

## Table of Contents

* [Required Packages](https://github.com/st-FPS/Smart_charging_prototypes#required-packages)
* [Structure](https://github.com/st-FPS/Smart_charging_prototypes#structure)
* [Inputs](https://github.com/st-FPS/Smart_charging_prototypes#inputs)
* [Outputs (tbc)](https://github.com/st-FPS/Smart_charging_prototypes#outputs)
* [Getting Started](https://github.com/st-FPS/Smart_charging_prototypes#getting-started)
* [Notes](https://github.com/st-FPS/Smart_charging_prototypes#notes)

## Required Packages

* pandas, numpy, os
* datetime
* time
* random
* glob
* pickle
* pulp

## Structure

* JLP_multi_opt.py:

This is the main file. It searches for different combinations of vehicles and chargers for a single store. It's used to find charging costs for a set of journeys under different conditions.

* lin_prog_functions.py

This includes all the linear programming functions:
optimise_range_3 iterates over each day and calls the linear opt
function for each category (optimisation or benchmark)

* testdata_proc.py

This contains the preprocessing functions to clean pricing data and
generate a skeleton schedule for all vehicles in a given time range.
It can be run as a standalone script to generate these outputs
independently as pickle files. JLP_multi_opt.py can be modified to read these
pickles instead of generating them each time.

* global_variables.py

This includes all the assumptions to use, as well as input file paths
for price and journey data. It also includes all the column names to
import and generate.

* output_functions.py

These are all the summary functions, aggregations and plots.

* Jupyter files are for prototyping and specific tests, fine to ignore.

## Inputs

Example files can be found in Azure (Z:\R&D Project Data\WEVC - Data Analytics Stream\WP8 - Smart Charging)

* Journey data

This is all the journeys including the ones in your focus time range,
already with an energy required calculation and a vehicle allocation.
Must include the columns in global_variables.py, line 21.
'vannumber_ev_' is the vehicle number.

Currently we're using journeys from a synthetic 2021

* Electricity pricing data

Electricity pricing for each half hour period (in pence).

## Outputs

Examples are in Azure (Z:\R&D Project Data\WEVC - Data Analytics Stream\WP8 - Smart Charging\Outputs)

* Range Figure - Electricity demand and costs for each day

* Heatplot - Electricity demand per time period for all dates

* Scatter Plot (optional) - How much charging occurs at each price point. Not very useful unless comparing different runs.

* Daily figures (optional) - These are plots of energy demand, # vehicles charging, costs and combined SoC for each day. They take a while to generate so leave out unless necessary.

* Settings File - Variables and settings used
* Range Profile (pkl) - Charging profile for the whole period, for all vehicles
* Site Profile (pkl) - Charging profile at site level
* Days Summary (pkl) - Daily aggregation of charging profiles
* Grid file (cvs) - Summary of main results for each run

* ## Getting Started

1) Modify global_variables.py:

    1) Line 22: Modify with outputs path
    2) Line 23: Modify with input folder with electricity prices and site capacity
    3) Line 24: Modify with your journey folder path.
    4) Line 7: modify with number of fast chargers
    5) Line 10-11: your range start time (when you want the schedule to start in the morning, it needs to be before the first arrival)
    6) Line 9: likely you just want to put `['opt']`. This is the list of categories to run ('opt' is smart charging, 'BAU' is the benchmark). It's likely not working well for running two scenarios at a time.
    7) Lines 32-41: change specifications for the stores (or add a new store)
    8) Line 45: Change the value of xPMG, the correction factor on WLTP fuel consumption (1 is no correction)
    9) Lines 47-119: if you want, change the specifications of the vehicles

2) Create the `Outputs\Logs\` folders

3) Modify JLP_multi_opt.py

   1) Lines 19: change branch to use
   1) Line 20: Select vehicles to use, as a list of lists.
   1) Line 21: change the number of vehicles of each type, following the structure of the vehicle list.
   1) Line 22: Select your chargers to use. This is in the shape of a
   list of lists, so `[[11,11], [22,22], [11,22]]` will perform a search
   with all 11 kW chargers, all 22 kW chargers and a mix of 11 and 22 kW.
   1) Line 23: Manually adjust the run # (to one that doesn't exist yet). This is for logging purposes.
   1) Line 24: Add some note to make your life easier
   1) Line 25: Select the year you're working with (to identify the journeys)
   1) Run P1_grid.py and good luck!

## Notes

* The benchmark is built in as their own optimiser functions. BAU
calculates a 'dumb' algorithm which charges each vehicle on arrival
without capacity constraint.

* Slide decks in [Sharepoint](https://flexpowerltd.sharepoint.com/:f:/s/WEVCMFC/ErXbpxa-1YtKo6P5XfcKhhIB92Bj8NSUSW9O0Oc_36hyGQ?e=X2TiLs)

## To Do

* Every day the schedule begins at a given time, so a day's schedule is from 8am to next day's 8am. If any arrivals happen before this time it will allocate that journey's energy requirements to the previous day's. So if a journey happens on Day 5 from 4 to 7 am it will be allocated to Day 4 and potentially lead to unfeasible scenarios. This is currently globally set in the global variables. Ideally a script should calculate the right start time according to the data.

* Currently each run requires manually changing the run number. This should be automatic.

* Several things can change when running the SC script: branch, vehicle types, number of type of vehicles, journey filepaths, electricity price path, outputs path, chargers, number of fast chargers, year, site capacity path, xPMG factor. At the moment most of these things are entered manually, this needs to change to run batches.

* Particuarly we need to change the way we feed the number of chargers for each case, which is currently a global variable.

* At the moment, os.path.join isn't working well with the Azure drive so only runs with local files.

* Currently this is very specific to the Waitrose data. We need to create common data schema.

* For pricing data, it's currently reading from the Time_Day_Workings file from Waitrose. This is a general price tariff because we don't have specific data for 2021. The function generates a price table for the date range where all the days look the same. We should use somehing more like clean_pricing function (from testdata_proc.py) for a real tariff table (predicted or historic).

* Often creating the profiles takes a long time. The profiles depend on journeys and pricing so if these stay the same for many batches, it's worthwile to save these profiles and reuse them. However, this only happens in specific cases such as when repeating optimisations for different powered AC chargers. So something has to be build for this specifically.

* The outputs need to be cleaned up
