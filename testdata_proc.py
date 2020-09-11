# Data processing functions for testing optimiser
# Started 1 Sept 2020

import numpy as np
from numpy.core.fromnumeric import shape
import pandas as pd
import datetime as dt
import glob
import pickle
import global_variables as gv
import functions as f
import random

def prep_data(path, category):
    all_files = glob.glob(path)
    journeys = pd.concat((pd.read_csv(f,usecols=gv.IMPORT_COLS) for f in all_files))
    non_ev = journeys[journeys['vannumber_ev_'] == 0].index
    journeys.drop(non_ev, inplace=True)
    journeys['Start_Time_of_Route']=pd.to_datetime(journeys['Start_Time_of_Route'])
    journeys['date'] = journeys['Start_Time_of_Route'].dt.date
    num_vehicles = journeys.groupby('date').max()['vannumber_ev_']
    quiet_days = num_vehicles[num_vehicles > 2 * gv.NUM_VEHICLES].index
    quiet_journeys = journeys['date'].isin(quiet_days)
    journeys = journeys[quiet_journeys]
    journeys.rename(columns={'vannumber_ev_':'Vehicle_ID'},inplace=True)
    journeys = limit_vehicles_multishift(journeys, category)
    journeys['End_Time_of_Route']=pd.to_datetime(journeys['End_Time_of_Route'])
    journeys.set_index(['date','Route_ID'],inplace=True)
    return journeys

def limit_vehicles_multishift(journeys, category):
    list_days = list(journeys.date.unique())
    journey_list = []
    for day in list_days:
        daily_journeys = journeys[journeys['date']==day]
        select_journeys = daily_journeys[
            daily_journeys['Vehicle_ID'].isin(gv.VANS[category])]
        journey_list.append(select_journeys)
    return pd.concat(journey_list)

def get_weeks_data(journeys, day,delta):
    """Takes a week worth of data (or some period) from the combined dataframe

    Args:
        journeys (DataFrame): dataframe of all journeys in a given period

    Returns:
        week: dataframe containing only the journeys in that week
    """

    week = journeys[(journeys.index.get_level_values('date').date >= day) 
    & (journeys.index.get_level_values('date').date < day + delta)]
    return week

def clean_pricing(path):
    import_cols = ['date', 'from', 'to', 'unit_rate_excl_vat']
    pricing = pd.read_csv(path, usecols=import_cols)
    pricing['from'] = pd.to_datetime(pricing['date'] + " " + pricing['from'])
    pricing['to'] = pd.to_datetime(pricing['date'] + " " + pricing['to'])
    return pricing

all_journeys = prep_data(gv.data_path, gv.CATEGORY)

#print(all_journeys.head(20))

# TODO: just get journey data for all vehicles in one day
prototype_week = get_weeks_data(all_journeys, gv.PROTOTYPE_DAYS[0], gv.TIME_RANGE)
price_data = clean_pricing(gv.pricing_path)
BAU_profile = f.BAU_charging(prototype_week, price_data)
BAU_profile_test = f.BAU_charging(test_week, price_data)

# Pickle
pickle.dump(all_journeys,open('Data/all_journeys','wb'))
pickle.dump(prototype_week,open('Data/prototype_week','wb'))
pickle.dump(test_week,open('Data/test_week','wb'))
pickle.dump(price_data,open('Data/price_data','wb'))
pickle.dump(BAU_profile,open('Data/BAU_profile','wb'))
pickle.dump(BAU_profile_test,open('Data/BAU_profile_test','wb'))

print(BAU_profile.head())

# print('Start time range:' , 
# min(prototype_week['Start_Time_of_Route']), max(prototype_week['Start_Time_of_Route']))

# print('End time range:' , 
# min(prototype_week['End_Time_of_Route']), max(prototype_week['End_Time_of_Route']))

