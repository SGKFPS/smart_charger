# Smart Charging Tool
This tool was developed to optimise the charging of a fleet of electric
vehicles according to various costs.

The current Phase 1 focuses on charging at low priced period while
maintining overall site below a global site capacity. There's also
functionality to charge to next day's requirements or to breach site
capacity if absolutely necessary. The optimisation is done using **PuLP**,
a linear programming package.

## Table of Contents

* [Required Packages](https://github.com/st-FPS/Smart_charging_prototypes#required-packages)
* [Structure](https://github.com/st-FPS/Smart_charging_prototypes#structure)
* [Inputs](https://github.com/st-FPS/Smart_charging_prototypes#inputs)
* Outputs (tbc)
* [Getting Started](https://github.com/st-FPS/Smart_charging_prototypes#getting-started-with-single-branch)
* [Getting Started with Multiple Branches](https://github.com/st-FPS/Smart_charging_prototypes#getting-started-with-multiple-branches)
* [Notes](https://github.com/st-FPS/Smart_charging_prototypes#notes)

## Required Packages
- pandas, numpy, os
- datetime
- time
- random
- glob
- pickle
- pulp

## Structure

- P1_grid.py:

This is the main file to run. It runs all the preprocessing functions
and runs a grid search for each combination of charger, site capacity.
It then produces outputs from daily and global aggregation and saves to
an Output folder

- Multi_store_grid_SC.py:

This is an alternative 'main file'. In this case the scrip searches
over a set of branches, for a single charger/capacity per branch.

- lin_prog_functions.py

This includes all the linear programming functions:
optimise_range_2 iterates over each day and calls the linear opt
function for each category (optimisation or benchmark)

- testdata_proc.py

This contains the preprocessing functions to clean pricing data and
generate a skeleton schedule for all vehicles in a given time range.
It can be run as a standalone script to generate these outputs
independently as pickle files. P1_grid.py can be modified to read these
pickles instead of generating them each time.

- global_variables.py

This includes all the assumptions to use, as well as input file paths
for price and journey data. It also includes all the column names to
import and generate.

- output_functions.py

These are all the summary functions, aggregations and plots.

- Jupyter files are for prototyping and specific tests, fine to ignore.

## Inputs
Example files can be found in Azure (Z:\R&D Project Data\WEVC - Data Analytics Stream\WP8 - Smart Charging)

- Journey data

This is all the journeys including the ones in your focus time range,
already with an energy required calculation and a vehicle allocation.
Must include the columns in global_variables.py, line 41.
'vannumber_ev_' is the vehicle number.

The current file we're using for 2019 Coulsdon Waitrose CFC data.

- Electricity pricing data

Electricity pricing for each half hour period (in pence).

- Allocation for multiple branches can be found in Azure (Z:\R&D Project Data\WEVC - Data Analytics Stream\WP7 - Historic Journey & Order Analysis\D7.1 - Feasibility, Cost and Emission Study\Study Outputs\Results\10.WEVC.allocated_journeys_focus.02.ST.csv)

## Getting Started with single branch:

1) Modify global_variables.py:

    1) Line 123: Modify with your journey data file. This is meant to
       concatenate several files so you can use the * for wildcard

    1) Line 124: Modify with path for pricing file

    2) Line 7-8: modify with number of vehicles and fast chargers

    3) Line 10: your range start time

    4) Line 11 (or 12): your time range to study (start with a week to get something fast)

    5) Line 17: likely you just want to put `['opt']`. This is the list of categories to run ('opt' is smart charging, 'BAU' and 'BAU2' are the two benchmarks)

    6) Lines 133-139: if you want, change the specifications of the Vivaro LR

2) Create the `Outputs\Logs\` folders

3) Modify P1_grid.py

    1) Line 22: Manually adjust the run # (to one that doesn't exist yet). This is for logging purposes.

    2) Lines 23, 24: change branch to use (just for logging, this won't change anything)

    3) Line 25: Select your chargers to use. This is in the shape of a
   list of lists, so `[[11,11], [22,22], [11,22]]` will perform a search
   with all 11 kW chargers, all 22 kW chargers and a mix of 11 and 22 kW.

    1) Line 26: List of site capacities to include in your grid search

    2) Lines 30-37: If you don't have the profiles already, leave them
   uncommented. If you have already generated it from the
   testdata_proc.py file, comment them and use lines 39-40.

    1) Run P1_grid.py and good luck!

## Getting Started with multiple branches:

1) Modify global_variables.py:

    1) Line 129: Modify with your journey data file (includes all branches)

    2) Line 10: range start time (if you choose to crop the journeys to a specific range)

    3) Line 11 (or 12): time range to study (start with a week to get something fast)

    4) Line 17: likely you just want to put `['BAU']`. This is the list of categories to run ('opt' is smart charging, 'BAU' and 'BAU2' are the two benchmarks)

    5) Lines 141-203: if you want, change the specifications of the Arrival vans
    6) Lines 207-235: change the vans and chargers to use in each store (or comment out stores you don't want to run)

2) Create the `Outputs\LogsJLP\` folders

3) Modify Multi_store_gridSC.py

    1) Line 21: Manually adjust the run # (to one that doesn't exist yet). This is for logging purposes.

    2) Lines 24-40: If you don't have the profiles already, leave them
   uncommented. If you have already generated them in a previous run, comment them and use lines 42-45.

    1) Run Multi_store_gridSC.py and good luck!

## Notes
- The benchmarks are built in as their own optimiser functions. BAU
calculates a 'dumb' algorithm which charges each vehicle on arrival
without capacity constraint. BAU2 is similar but obeys site capacity
limit. Both of them are less relevant in recent iterations so you
likely just want to run the 'opt' case and get a general benchmark for
comparison.

- Slide decks in [Sharepoint](https://flexpowerltd.sharepoint.com/:f:/s/WEVCMFC/ErXbpxa-1YtKo6P5XfcKhhIB92Bj8NSUSW9O0Oc_36hyGQ?e=X2TiLs)
