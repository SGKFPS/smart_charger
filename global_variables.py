# Global variables to use in all calculations
# Created 1 September 2020

import datetime as dt

NUM_VEHICLES = 10
TIME_INT = dt.timedelta(minutes = 30)
RANDOM_SOC_RATIO = 0.2 # randomness introduced into the journey state of charge reqs
REFR_RATIO = 0.25 #ratio of exta energy use for refrigeration (kWh/km)
POWER_KM = 0.29 # kWh / mile
TIME_RANGE = dt.timedelta(weeks=1, days=1)
PROTOTYPE_DAYS = [dt.date(2019,2,10), dt.date(2019,6,22), dt.date(2019,10,19)]
TEST_DAYS = [dt.date(2019,2,17), dt.date(2019,6,29), dt.date(2019,10,26)]
DAY = dt.datetime(2019,2,10)
CHARGER_POWER = 7 # kW
VANS = {'PROT': [3, 4, 6, 7, 8, 13, 14, 15, 16, 18],
'TEST': [0, 1, 2, 5, 9, 10, 11, 12, 17, 19]}
CATEGORY = 'PROT'
NUM_CHARGERS = NUM_VEHICLES
POWER_INT = CHARGER_POWER * TIME_INT / dt.timedelta(hours=1)
CHARGER_EFF = 0.9
BATTERY_CAPACITY = 75 #kWh
SITE_CAPACITY = 20 # kWh (in a half-hour period so eq. 50 kW)
CHAR_ST = dt.time(11, 0,0) # 11 am is start of charging period each day #FIXME Make this data dependent
CHAR_ST_DELTA = dt.timedelta(hours=11)

TIME_FRACT = 0.5
DAY_INTERVALS = 48
IMPORT_COLS = ['Route_ID', 'Branch_ID', 'Start_Time_of_Route',
                'End_Time_of_Route', 'Energy_Required','vannumber_ev_'] 

data_path = r"Data/JPL_allocation/Vivaro/*.csv"
pricing_path = r"Data/Octopus Agile Rates_2019_LON.csv"

# Column names
SOC = {} 
for i in range(NUM_VEHICLES):
    SOC[i] = 'SOC_{}'.format(i)

Power_output = {}
for i in range(NUM_VEHICLES):
    Power_output[i] = 'Output_{}'.format(i)