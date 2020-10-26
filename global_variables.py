# Global variables to use in all calculations. Phase 2
# Created 26 October 2020

import datetime as dt
import os

NUM_VEHICLES = 10
NUM_FAST_CH = 5
TIME_INT = dt.timedelta(minutes=30)
START_DT = dt.datetime(2019, 3, 21, 0, 0, 0)
# TIME_RANGE = dt.timedelta(weeks=30, days=4)
TIME_RANGE = dt.timedelta(weeks=0,days=4)
DAY = START_DT

CHARGER_EFF = 0.9
MARGIN_SOC = 0.1  # Required SOC will be 10% more than planned
CATS = ['opt']  # 'opt' 'BAU', 'BAU2']
CHAR_ST = dt.time(8, 0, 0)  # FIXME Make this data dependent
CHAR_ST_DELTA = dt.timedelta(hours=8)
DAY_INTERVALS = 48
EPRICE = 14  # (p) Temp value #FIXME
REF_CONS = 0.5

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
TIME_FRACT = TIME_INT / dt.timedelta(hours=1)

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

# For grid_P1:
data_path = r"Inputs/JPL_allocation/Vivaro_513-22kW_2019/164_newstoreE*.csv"
pricing_path = r"Inputs/Octopus Agile Rates_2019_LON.csv"
# pricing_path = r'Inputs/20-06.JLP.current_forecast_tariff_2019.02.BF.csv'
LOGS1 = os.path.join('Outputs', 'Logs')

# For Multi_store_gridSC
multi_journey_path = r'../Journey_analysis/JLP2/Outputs/allocated_journeys.csv'
LOGS = os.path.join('Outputs', 'LogsJLP')

VSPEC = {
    'Vivaro_LR':{
        'D':0.29,   # Quoted kWh/mile
        'C':75,     # Quoted pack capacity
        'P':1000,    # Payload
        'N':'Volkswagen eCrafter',
        'color':'tab:green',
        'Ref':0.5
    },
    'Arrival44':{
        'D':0.436,   # Quoted kWh/mile 80% d.o.d
        #'D':0.545,   # Quoted kWh/mile 100%
        'C':44,     # Quoted pack capacity
        'P':2225,    # Payload
        'R':80.8,
        'N':'Arrival 44kW',
        'color':'tab:green',
        'Ref':0.5,
        'df':'df_44'
    },
    'Arrival67':{
        'D':0.479,   # Quoted kWh/mile 80%
        #'D':0.599,   # Quoted kWh/mile 100%
        'C':67,     # Quoted pack capacity
        'P':2017,    # Payload
        'R':111.8,
        'N':'Arrival 67kW',
        'color':'tab:orange',
        'Ref':0.5,
        'df':'df_67'
    },
    'Arrival89':{
        'D':0.477,   # Quoted kWh/mile 80%
        #'D':0.597,   # Quoted kWh/mile 100%
        'C':89,     # Quoted pack capacity
        'P':1818,    # Payload
        'R':149,
        'N':'Arrival 89kW',
        'color':'tab:red',
        'Ref':0.5,
        'df':'df89'
    },
    'Arrival111':{
        'D':0.493,   # Quoted kWh/mile 80%
        #'D':0.616,   # Quoted kWh/mile 100%
        'C':111,     # Quoted pack capacity
        'P':1619,    # Payload
        'R':180,
        'N':'Arrival 111kW',
        'color':'tab:purple',
        'Ref':0.5,
        'df':'df_111'
    },
    'Arrival133':{
        'D':0.504,   # Quoted kWh/mile 80%
        #'D':0.630,   # Quoted kWh/mile 100%
        'C':133,     # Quoted pack capacity
        'P':1420,    # Payload
        'R':211,
        'N':'Arrival 130kW',
        'color':'tab:olive',
        'Ref':0.5,
        'df':'df_133'
    },
    'Sprinter':{
        'D':0.149542468,   # Quoted l/mile
        'C':2000,    # Very high mock value to remove constraint
        'P':1235,    # Payload
        'N':'Mercedes Sprinter PV',
        'color':'tab:olive',
        'price':36775,
        'Ref':0.162
    }
}

STORE_SPEC = {
   # 193:{
   #    'V':'Arrival44',
   #    'CH':[7, 7]
   # },
   # 194:{
   #    'V':'Arrival89',
   #    'CH':[7, 7]
   # },
   # 199:{
   #    'V':'Arrival67',
   #    'CH':[11, 11]
   # },
   # 211:{
   #    'V':'Arrival89',
   #    'CH':[7, 7]
   # },
   226:{
      'V':'Arrival133',
      'CH':[11, 11]
   },
   457:{
      'V':'Arrival133',
      'CH':[22, 22]
   },
   513:{
      'V':'Arrival111',
      'CH':[11, 11]
   }
}