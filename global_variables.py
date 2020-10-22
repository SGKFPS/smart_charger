# Global variables to use in all calculations
# Created 1 September 2020

import datetime as dt

NUM_VEHICLES = 10
NUM_FAST_CH = 5
TIME_INT = dt.timedelta(minutes=30)
START_DT = dt.datetime(2019, 3, 1, 0, 0, 0)
#TIME_RANGE = dt.timedelta(weeks=52, days=4)
TIME_RANGE = dt.timedelta(weeks=0,days=4)
DAY = START_DT

CHARGER_EFF = 0.9
BATTERY_CAPACITY = 75  # kWh
MARGIN_SOC = 0.1  # Required SOC will be 10% more than planned
CATS = ['opt'] #, 'BAU', 'BAU2']
CHAR_ST = dt.time(11, 0, 0)  # FIXME Make this data dependent
CHAR_ST_DELTA = dt.timedelta(hours=11)
DAY_INTERVALS = 48

# Select set of vans to use for prototyping or testing.
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
TIME_FRACT = TIME_INT / dt.timedelta(hours=1)
# POWER_INT = CHARGER_POWER * TIME_FRACT

IMPORT_COLS = ['Route_ID', 'Branch_ID', 'Start_Time_of_Route',
               'End_Time_of_Route', 'Energy_Required', 'vannumber_ev_']

LEVELS = ['Main', 'Tonext', 'Breach', 'Magic', 'Empty']

FPS_BLUE = '#004A9C'
FPS_GREEN = '#45D281'
FPS_YELLOW = '#FEC001'
FPS_PURPLE = '#A365E0'

CAT_COLS = {
    'PRICE': {
        'opt': 'Electricity_Price',
        'BAU': 'Time_Price',
        'BAU2': 'Time_Price'
    },
    'OUTPUT': {
       'opt': 'Output_Opt',
       'BAU': 'Output_BAU',
       'BAU2': 'Output_BAU2'
    },
    'CH_TYPE': {
       'opt': 'Ch_Opt',
       'BAU': 'Ch_BAU',
       'BAU2': 'Ch_BAU2'
    },
    'CHARGE_DEL': {
       'opt': 'ChDelivered_Opt',
       'BAU': 'ChDelivered_BAU',
       'BAU2': 'ChDelivered_BAU2'
    },
    'ECOST': {
       'opt': 'ECost_Opt',
       'BAU': 'ECost_BAU',
       'BAU2': 'ECost_BAU2'
    },
    'SOC': {
       'opt': 'SoC_Opt',
       'BAU': 'SoC_BAU',
       'BAU2': 'SoC_BAU2'
    },
    'PEAK': {
       'opt': 'Peak_Opt',
       'BAU': 'Peak_BAU',
       'BAU2': 'Peak_BAU2'
    },
    'NUM': {
       'opt': 'N_Opt',
       'BAU': 'N_BAU',
       'BAU2': 'N_BAU2'
    },
    'BREACH': {
       'opt': 'Br_Opt',
       'BAU': 'Br_BAU',
       'BAU2': 'Br_BAU2'
    },
    'LEVEL': {
       'opt': 'Level_Opt',
       'BAU': 'Level_BAU',
       'BAU2': 'Level_BAU2'
    }
}

COLOR = {
    'opt': FPS_YELLOW,
    'BAU': FPS_BLUE,
    'BAU2': FPS_GREEN
 }

ALPHA = {
    'opt': 1,
    'BAU': 0.6,
    'BAU2': 0.6
 }

LABELS = {
    'opt': 'Smart Charging',
    'BAU': 'Unconstrained benchmark',
    'BAU2': 'Constrained benchmark'
 }
data_path = r"Inputs/JPL_allocation/Vivaro_513-22kW_2019/164_newstoreE*.csv"
pricing_path = r"Inputs/Octopus Agile Rates_2019_LON.csv"

# Column names
SOC = {}
for i in range(NUM_VEHICLES):
    SOC[i] = 'SOC_{}'.format(i)

Power_output = {}
for i in range(NUM_VEHICLES):
    Power_output[i] = 'Output_{}'.format(i)
