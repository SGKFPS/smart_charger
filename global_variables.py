# Global variables to use in all calculations
# Created 1 September 2020

import datetime as dt

NUM_VEHICLES = 20
TIME_INT = dt.timedelta(minutes = 30)
RANDOM_SOC_RATIO = 0.2 # randomness introduced into the journey state of charge reqs
REFR_RATIO = 0.25 #ratio of exta energy use for refrigeration (kWh/km)
POWER_KM = 0.29 # kWh / mile
START_DT = dt.datetime(2019,2,1,0,0,0)
TIME_RANGE = dt.timedelta(weeks=1, days=1)
DAY = dt.datetime(2019,2,10)
CHARGER_POWER = 21 # kW
CATS = ['opt','BAU']
VANS = {
    'PROT': [
        3, 4, 6, 11, 12, 14, 
        16, 20, 22, 23, 24, 25, 26, 
        29, 30, 31, 34, 35, 38, 39,
        42, 43],
    'TEST': [
        44, 1, 2, 5, 7, 8, 9, 10, 
        13, 15, 17, 18, 19, 21, 27,
        28, 32, 33, 36, 37, 40, 41
        ]
    }
CATEGORY = 'PROT'
NUM_CHARGERS = NUM_VEHICLES
POWER_INT = CHARGER_POWER * TIME_INT / dt.timedelta(hours=1)
CHARGER_EFF = 0.9
BATTERY_CAPACITY = 75 #kWh
SITE_CAPACITY = {
    'opt': 150,  # kWh (in a half-hour period so eq. 200 kW)
    'BAU': 10000,
    'BAU2': 150
 }
CHAR_ST = dt.time(11, 0,0) # 11 am is start of charging period each day #FIXME Make this data dependent
CHAR_ST_DELTA = dt.timedelta(hours=11)

TIME_FRACT = 0.5
DAY_INTERVALS = 48
IMPORT_COLS = ['Route_ID', 'Branch_ID', 'Start_Time_of_Route',
                'End_Time_of_Route', 'Energy_Required','vannumber_ev_'] 

CAT_COLS = {
    'PRICE' : {
        'opt': 'Electricity_Price',
        'BAU': 'Time_Price',
        'BAU2': 'Time_Price'
    },
    'OUTPUT' : {
       'opt': 'Output_Opt',
       'BAU': 'Output_BAU',
       'BAU2': 'Output_BAU2' 
    },
    'CHARGE_DEL' : {
       'opt': 'ChDelivered_Opt',
       'BAU': 'ChDelivered_BAU',
       'BAU2': 'ChDelivered_BAU2' 
    },
    'ECOST' : {
       'opt': 'ECost_Opt',
       'BAU': 'ECost_BAU',
       'BAU2': 'ECost_BAU2' 
    },
    'SOC' : {
       'opt': 'SoC_Opt',
       'BAU': 'SoC_BAU',
       'BAU2': 'SoC_BAU2'         
    },
    'PEAK' : {
       'opt': 'Peak_Opt',
       'BAU': 'Peak_BAU',
       'BAU2': 'Peak_BAU2'         
    },
    'NUM' : {
       'opt': 'N_Opt',
       'BAU': 'N_BAU',
       'BAU2': 'N_BAU2'         
    }
}

COLOR = {
    'opt': 'tab:blue',  # kWh (in a half-hour period so eq. 200 kW)
    'BAU': 'tab:green',
    'BAU2': 'tab:purple'
 }
data_path = r"Data/JPL_allocation/Vivaro/*.csv"
pricing_path = r"Data/Octopus Agile Rates_2019_LON.csv"

# Column names
SOC = {} 
for i in range(NUM_VEHICLES):
    SOC[i] = 'SOC_{}'.format(i)

Power_output = {}
for i in range(NUM_VEHICLES):
    Power_output[i] = 'Output_{}'.format(i)