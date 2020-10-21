This tool was developed to optimise the charging of a fleet of electric
vehicles according to various costs.

The current Phase 1 focuses on charging at low priced period while
maintining overall site below a global site capacity. There's also
functionality to charge to next day's requirements or to breach site
capacity if absolutely necessary. The optimisation is done using PuLP,
a linear programming package.

# See also

Slide decks in [Sharepoint](https://flexpowerltd.sharepoint.com/:f:/s/WEVCMFC/ErXbpxa-1YtKo6P5XfcKhhIB92Bj8NSUSW9O0Oc_36hyGQ?e=X2TiLs)

# Required Packages
- pandas, numpy, os
- datetime
- time
- random
- glob
- pickle
- pulp

# Structure

- P1_grid.py:

This is the main file to run. It runs all the preprocessing functions
and runs a grid search for each combination of charger, site capacity.
It then produces outputs from daily and global aggregation and saves to
an Output folder

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

# Inputs
Example files can be found in [Azure](Z:\R&D Project Data\WEVC - Data Analytics Stream\WP8 - Smart Charging)

- Journey data

This is all the journeys including the ones in your focus time range,
already with an energy required calculation and a vehicle allocation.
Must include the columns in global_variables.py, line 41.
'vannumber_ev_' is the vehicle number.

The current file we're using for 2019 Coulsdon Waitrose CFC data.

- Electricity pricing data

Electricity pricing for each half hour period (in pence).

# Getting Started

1) Modify global_variavels.py:

    a) Modify lines 108 and 109 with your file paths for journeys and
   pricing.

    b) Modify lines 6 and 7 with number of vehicles and number of fast
       chargers

    c) Modify lines 9 and 12 for your range start time (sorry, you have
       to do both!)

    d) Modify line 10 for your time range to study

    e) If you want to calculate a benchmark, uncomment them from the
       list in line 17 (but think about using a single charger power)

    f) Change battery capacity to your vehicle spec

2) Modify P1_grid.py

    a) Line 22: Manually adjust the run # (to one that doesn't exist
       yet). This is for logging purposes.

    b) Line 24: Select your chargers to use. This is in the shape of a
       list of lists, so

       ```bash
       [[11,11], [22,22], [11,22]]
       ```

       will perform a search with all 11 kW chargers, all 22 kW
       chargers and a mix of 11 and 22 kW.

    c) Line 25: List of site capacities to include in your grid search

    d) Lines 28-35: If you don't have the profiles already, leave them
       uncommented. If you have already generated it from the
       testdata_proc.py file, comment them and use lines 37-38.

    e) Run P1_grid.py and good luck!

# Notes
- The benchmarks are built in as their own optimiser functions. BAU
calculates a 'dumb' algorithm which charges each vehicle on arrival
without capacity constraint. BAU2 is similar but obeys site capacity
limit. Both of them are less relevant in recent iterations so you
likely just want to run the 'opt' case and get a general benchmark for
comparison.
