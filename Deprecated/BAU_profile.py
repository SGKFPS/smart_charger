# Benchmark scheduling
# Creates a charging profile that charges each vehicle at max power as soon as they return to depot
# Started 03 September 2020

import numpy as np
import pandas as pd
import datetime as dt
from pulp import *
import pickle
import global_variables as gv
import functions as f

# Import journey and price data

prot_journeys = pickle.load(open('Data/prototype_week','rb'))
test_journeys = pickle.load(open('Data/test_week','rb'))
electricity_price = pickle.load(open('Data/price_data','rb'))

charging_profile = f.dumb_charging(prot_journeys, electricity_price)

pickle.dump(charging_profile,open('Data/BAU_profile','wb'))

# Test stuff
# date1 = dt.datetime(2020,2,16,0,0,0)
# single_profile = f.single_BAU_schedule(prot_journeys, date1, 8, electricity_price[['from']])