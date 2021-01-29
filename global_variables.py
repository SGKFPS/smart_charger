# Global variables to use in all calculations. Phase 2
# Created 26 October 2020

import datetime as dt
import os

NUM_FAST_CH = 5
YEAR = 2021
CATS = ['opt']  # 'opt' 'BAU', 'BAU2'
CHAR_ST = dt.time(8, 0, 0)  # FIXME Make this data dependent
CHAR_ST_DELTA = dt.timedelta(hours=8)
CHARGER_EFF = 0.9  # Global efficiency value
MARGIN_SOC = 0.1  # Required SOC margin (when not full)
IS_LEEWAY = dt.timedelta(minutes=60)  # Time for connection how much time you assume the vehicles were charged for
TURNAROUND = dt.timedelta(minutes=60)  # Min turnaround time
REF_CONS = 0  # Refrigeration use. Zero if already accounted for.
TIME_INT = dt.timedelta(minutes=30)
TIME_FRACT = TIME_INT / dt.timedelta(hours=1)
DAY_INTERVALS = 48

# Paths
LOGS = os.path.join('Outputs', 'LogsMixed')  # Where the outputs go
INPUTS = 'Inputs'  # Site capacity, tariffs
JOURNEYS = 'Inputs'

IMPORT_COLS = ['Route_ID', 'Branch_ID', 'Start_Time_of_Route',
               'End_Time_of_Route', 'Energy_Required', 'vannumber_ev_']

LEVELS = ['Main', 'Tonext', 'Breach', 'Magic', 'Empty']

STORE_SPEC = {
   457:{
      'ASC': 250,
      'N': 'Pontprennau',
      'zMax': 150
   },
   513:{
      'ASC': 900,
      'N': 'Coulsdon CFC',
      'zMax': 700  # z-range for heatplot
   }
}

# Vehicle Specs
xPMG = 1  # Fuel correction factor from WLTP figures
VSPEC = {
    'Vivaro_LR':{
        'D':0.29,   # Quoted kWh/mile
        'C':75,     # Quoted pack capacity
        'P':1000,    # Payload
        'N':'Vivaro Long Range',
        'color':'tab:green',
        'Ref':0.5
    },
    'Arrival44': {
        'D': 0.436/xPMG,   # Quoted kWh/mile 80%
        # 'D':0.545,   # Quoted kWh/mile 100%
        'C100': 44,      # Quoted pack capacity
        'C': 35.2,         # 80% capacity
        'P': 2225,    # Payload
        'R': 80.8*xPMG,
        'N': 'Arrival 44 kWh',
        'color': 'tab:green',
        'Ref': 0.5,
        'df': 'df_44',
        'price': 37435
    },
    'Arrival67': {
        'D': 0.479/xPMG,   # Quoted kWh/mile 80%
        # 'D': 0.599,   # Quoted kWh/mile 100%
        'C100': 67,     # Quoted pack capacity
        'C': 53.6,   # 80% capacity
        'P': 2017,    # Payload
        'R': 111.8*xPMG,
        'N': 'Arrival 67 kWh',
        'color': 'tab:orange',
        'Ref': 0.5,
        'df': 'df_67',
        'price': 41389
    },
    'Arrival89': {
        'D': 0.477/xPMG,   # Quoted kWh/mile 80%
        # 'D': 0.597,   # Quoted kWh/mile 100%
        'C100': 89,     # Quoted pack capacity
        'C': 71.2,        # 80% capacity
        'P': 1818,    # Payload
        'R': 149*xPMG,
        'N': 'Arrival 89 kWh',
        'color': 'tab:red',
        'Ref': 0.5,
        'df': 'df89',
        'price': 45170
    },
    'Arrival111': {
        'D': 0.493/xPMG,   # Quoted kWh/mile 80%
        # 'D': 0.616,   # Quoted kWh/mile 100%
        'C100': 111,     # Quoted pack capacity
        'C': 88.8,        # 80% capacity
        'P': 1619,    # Payload
        'R': 180*xPMG,
        'N': 'Arrival 111 kWh',
        'color': 'tab:purple',
        'Ref': 0.5,
        'df': 'df_111',
        'price': 48952
    },
    'Arrival133': {
        'D': 0.504/xPMG,   # Quoted kWh/mile 80%
        # 'D': 0.630,   # Quoted kWh/mile 100%
        'C100': 133,     # Quoted pack capacity
        'C': 106.4,       # 80% capacity
        'P': 1420,    # Payload
        'R': 211*xPMG,
        'N': 'Arrival 133 kWh',
        'color': 'tab:olive',
        'Ref': 0.5,
        'df': 'df_133',
        'price': 52733
    },
}

CAT_COLS = {
    'PRICE': {
        'opt': 'Electricity_Price',
        'BAU': 'Time_Price',
    },
    'OUTPUT': {
       'opt': 'Output_Opt',
       'BAU': 'Output_BAU',
    },
    'CH_TYPE': {
       'opt': 'Ch_Opt',
       'BAU': 'Ch_BAU',
    },
    'CHARGE_DEL': {
       'opt': 'ChDelivered_Opt',
       'BAU': 'ChDelivered_BAU',
    },
    'ECOST': {
       'opt': 'ECost_Opt',
       'BAU': 'ECost_BAU',
    },
    'SOC': {
       'opt': 'SoC_Opt',
       'BAU': 'SoC_BAU',
    },
    'PEAK': {
       'opt': 'Peak_Opt',
       'BAU': 'Peak_BAU',
    },
    'NUM': {
       'opt': 'N_Opt',
       'BAU': 'N_BAU',
    },
    'BREACH': {
       'opt': 'Br_Opt',
       'BAU': 'Br_BAU',
    },
    'LEVEL': {
       'opt': 'Level_Opt',
       'BAU': 'Level_BAU',
    }
}

FPS_BLUE = '#004A9C'
FPS_GREEN = '#45D281'
FPS_YELLOW = '#FEC001'
FPS_PURPLE = '#A365E0'

COLOR = {
    'opt': FPS_YELLOW,
    'BAU': FPS_BLUE,
 }

ALPHA = {
    'opt': 1,
    'BAU': 0.6,
    'BAU2': 0.6
 }

LABELS = {
    'opt': 'Smart Charging',
    'BAU': 'Unconstrained benchmark',
 }