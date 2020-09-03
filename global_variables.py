# Global variables to use in all calculations
# Created 1 September 2020

import datetime as dt

NUM_VEHICLES = 10
NUM_CHARGERS = 10
RANDOM_SOC_RATIO = 0.2 # randomness introduced into the journey state of charge reqs
REFR_RATIO = 0.25 #ratio of exta energy use for refrigeration (kWh/km)
POWER_KM = 0.29 # kWh / mile
TIME_RANGE = dt.timedelta(weeks=1, days=1)
PROTOTYPE_DAYS = [dt.date(2020,2,10), dt.date(2020,6,22), dt.date(2020,10,19)]
TEST_DAYS = [dt.date(2020,2,17), dt.date(2020,6,29), dt.date(2020,10,26)]
CHARGER_POWER = 7 # kW
BATTERY_CAPACITY = 75 #kWh
CHAR_ST = dt.time(11, 0,0) # 11 am is start of charging period each day #FIXME Make this data dependent
CHAR_ST_DELTA = dt.timedelta(hours=11)
TIME_INT = dt.timedelta(minutes = 30)
DAY_INTERVALS = 48

data_path = r"Data/JPL_allocation/eSprinterHi39TRange_storeE/Prototype_branches/6.3/*.csv"
pricing_path = r"Data/Octopus Agile Rates_2019_LON.csv"

# Column names
SOC = {} 
for i in range(NUM_VEHICLES):
    SOC[i] = 'SOC_{}'.format(i)

Power_output = {}
for i in range(NUM_VEHICLES):
    Power_output[i] = 'Output_{}'.format(i)