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
    journeys.rename(columns={'vannumber_ev_':'Vehicle_ID'},inplace=True)
    journeys = limit_vehicles_multishift(journeys, category)
    journeys['End_Time_of_Route']=pd.to_datetime(journeys['End_Time_of_Route'])
    journeys = remove_busy_routes(journeys)
    journeys = get_prev_arrival(journeys)
    journeys.sort_values(by = ['date','Route_ID'], inplace=True)
    journeys.set_index(['date','Route_ID'],inplace=True)
    return journeys

# Selects vans to use
def limit_vehicles_multishift(journeys, category):
    list_days = list(journeys.date.unique())
    vans= gv.VANS[gv.CATEGORY][:gv.NUM_VEHICLES]
    journey_list = []
    for day in list_days:
        daily_journeys = journeys[journeys['date']==day]
        select_journeys = daily_journeys[
            daily_journeys['Vehicle_ID'].isin(vans)]
        journey_list.append(select_journeys)
    return pd.concat(journey_list)

# Get column for previous arrival time for each van
def get_prev_arrival(journeys):
    vans = journeys['Vehicle_ID'].unique()
    print(vans)
    van_journeys_list = []
    for van in vans:
        van_journeys = journeys[journeys['Vehicle_ID'] == van].copy()
        van_journeys.sort_values(
            by=['Start_Time_of_Route'],
            inplace=True,
            ascending=False)
        next_departure = dt.datetime.combine(
            max(journeys['date']),
            dt.datetime.min.time()
        ) + dt.timedelta(days=1, hours=6)
        for idx in van_journeys.index:
            van_journeys.loc[idx, 'Next_Departure'] = next_departure
            next_departure = van_journeys.loc[idx, 'Start_Time_of_Route']
        van_journeys.sort_values(by=['Start_Time_of_Route'], inplace=True)
        previous_arrival = dt.datetime.combine(
            min(journeys['date']),
            dt.datetime.min.time())
        for idx in van_journeys.index:
            van_journeys.loc[idx, 'Previous_Arrival'] = previous_arrival
            previous_arrival = van_journeys.loc[idx, 'End_Time_of_Route']
        van_journeys_list.append(van_journeys)
    return pd.concat(van_journeys_list)

# Removes routes that require more than the battery capacity
def remove_busy_routes(journeys):
    all_vehicles = journeys.groupby(['date','Vehicle_ID']).sum()
    busy_dates = all_vehicles[
        all_vehicles['Energy_Required'] > gv.BATTERY_CAPACITY*0.8
        ].index
    bad_routes = []
    while len(busy_dates) > 0:
        for busy in busy_dates:
            busy_routes = journeys[
            (journeys['date'] == busy[0])
            & (journeys['Vehicle_ID'] == busy[1])]['Route_ID']
            bad_routes.append(busy_routes.iloc[-1])
        clean_journeys = journeys[~journeys['Route_ID'].isin(bad_routes)]
        all_vehicles = clean_journeys.groupby(['date','Vehicle_ID']).sum()
        busy_dates = all_vehicles[
            all_vehicles['Energy_Required'] > gv.BATTERY_CAPACITY*0.8
            ].index
    return clean_journeys

def get_range_data(journeys, day,delta):
    """Takes a week worth of data (or some period) from the combined dataframe

    Args:
        journeys (DataFrame): dataframe of all journeys in a given period

    Returns:
        week: dataframe containing only the journeys in that week
    """

    week = journeys[(journeys.index.get_level_values('date') >= day) 
    & (journeys.index.get_level_values('date') < day + delta)]
    return week

def clean_pricing(path):
    import_cols = ['date', 'from', 'to', 'unit_rate_excl_vat']
    pricing = pd.read_csv(path, usecols=import_cols)
    pricing['from'] = pd.to_datetime(pricing['date'] + " " + pricing['from'])
    pricing['to'] = pd.to_datetime(pricing['date'] + " " + pricing['to'])
    pricing['Time_Price'] = list(range(len(pricing)))
    pricing.rename(columns={'unit_rate_excl_vat':'Electricity_Price'}, inplace=True)
    return pricing

all_journeys = prep_data(gv.data_path, gv.CATEGORY)


journeys_range = get_range_data(all_journeys, gv.DAY, gv.TIME_RANGE)
price_data = clean_pricing(gv.pricing_path)
empty_profile = f.create_empty_schedule(journeys_range, price_data)

# # Pickle
pickle.dump(all_journeys,open('Outputs/all_journeys','wb'))
pickle.dump(journeys_range,open('Outputs/journeys_range','wb'))
pickle.dump(price_data,open('Outputs/price_data','wb'))
pickle.dump(empty_profile,open('Outputs/empty_profile','wb'))

