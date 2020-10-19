# Data processing functions for testing optimiser
# Started 1 Sept 2020

import numpy as np
from numpy.core.fromnumeric import shape
import pandas as pd
import datetime as dt
import glob
import pickle
import global_variables as gv
import random
import time

def prep_data(path, category):
    """Preprocess journey data

    Formats datetimes, selects vans to use, gets next departure/previous arrival

    Args:
        path (str): filepath of journey data
        category (str): 'PROT' or 'TEST'

    Returns:
        DataFrame: table of all journeys
    """
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
    #journeys = remove_busy_routes(journeys)
    journeys = get_prev_arrival(journeys)
    journeys.sort_values(by = ['date','Route_ID'], inplace=True)
    journeys.set_index(['date','Route_ID'],inplace=True)
    return journeys

def limit_vehicles_multishift(journeys, category):
    """Selects only a subset of vans to use

    Args:
        journeys (DataFrame): table of all journeys for all vans
        category (str): 'PROT' or 'TEST'

    Returns:
        DataFrame: only journeys made by the subset of vans
    """
    list_days = list(journeys.date.unique())
    vans= gv.VANS[gv.CATEGORY][:gv.NUM_VEHICLES]
    journey_list = []
    for day in list_days:
        daily_journeys = journeys[journeys['date']==day]
        select_journeys = daily_journeys[
            daily_journeys['Vehicle_ID'].isin(vans)]
        journey_list.append(select_journeys)
    return pd.concat(journey_list)

def get_prev_arrival(journeys):
    """Get column for previous arrival time / next departure for each van

    Args:
        journeys (DataFrame): table of all journeys per vehicle

    Returns:
        DataFrame: same table as input with aditional information
    """
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
    """Removes journeys that require more than 100% battery

    Removes one journey at a time from days that go over 100% battery
    capacity per vehicle.

    Args:
        journeys (DataFrame): table of journeys

    Returns:
        DataFrame: cleaned table of journeys
    """
    all_vehicles = journeys.groupby(['date','Vehicle_ID']).sum()
    busy_dates = all_vehicles[
        all_vehicles['Energy_Required'] > gv.BATTERY_CAPACITY
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
            all_vehicles['Energy_Required'] > gv.BATTERY_CAPACITY
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
    """Creates df with electricity and time price

    This produces a list of electricity prices for each time period. It also creates
    a fake increasing 'time price' to use for benchmarking.
    Args:
        path (str): filepath of electricity price

    Returns:
        DataFrame: [description]
    """
    import_cols = ['date', 'from', 'to', 'unit_rate_excl_vat']
    pricing = pd.read_csv(path, usecols=import_cols)
    pricing['from'] = pd.to_datetime(pricing['date'] + " " + pricing['from'])
    pricing['to'] = pd.to_datetime(pricing['date'] + " " + pricing['to'])
    pricing['Time_Price'] = list(range(len(pricing)))
    pricing['Time_Price'] = pricing['Time_Price']/1000
    pricing.rename(columns={'unit_rate_excl_vat':'Electricity_Price'}, inplace=True)
    return pricing

def create_range_times(time_range,eprice):
    """Creates the timeline for a given range with the price information

    Args:
        time_range (list): list of 2 elements: start/end datetime
        eprice (DataFrame): table of electricity price

    Returns:
        DataFrame: dataframe of timeperiods with electricity price
    """
    mask = ( (eprice['from'] >= time_range[0]) 
    & (eprice['from'] < time_range[1]))
    timeline = eprice[mask][['from','Electricity_Price','Time_Price']].copy()
    timeline['date'] = pd.to_datetime((timeline['from'] - gv.CHAR_ST_DELTA).dt.date)
    return timeline

def create_empty_schedule(journeys, eprice):
    """Creates a empty schedule for each vehicle in a range

    Includes journey information as availability and energy consumption

    Args:
        journeys (DataFrame): Contains Start/End time of each route.
            Also includes next start date and energy req.
        eprice (DataFrame): electricity price for each time period.
            Also contains equivalent 'time price' for benchmark.

    Returns:
        DataFrame: Table of each time period for each vehicle with charge and
            discharge information
    """
    start_date = min(journeys.index.get_level_values('date')).to_pydatetime()
    start_range = dt.datetime.combine(start_date.date(), gv.CHAR_ST)
    end_date = max(journeys.index.get_level_values('date')).to_pydatetime()
    end_range = dt.datetime.combine(end_date.date(), gv.CHAR_ST)
    time_range = [start_range, end_range]
    num_days = (end_date.date() - start_date.date()).days
    # days_profile = {}
    vehicles = journeys['Vehicle_ID'].unique()
    veh_profiles_list = []
    for vehicle in vehicles:
        print('Vehicle:' ,vehicle)
        veh_profile = create_range_times(
            time_range,
            eprice
        )
        veh_profile['Vehicle_ID'] = vehicle
        veh_profile['Available'] = 1
        veh_profile['Battery_Use'] = 0
        # Get journeys for that vehicle
        veh_journeys = journeys[journeys['Vehicle_ID'] == vehicle].droplevel('date')
        veh_journeys = veh_journeys.sort_values(by='Start_Time_of_Route')

        # Assign 0 to availability when vehicle is out
        for route in veh_journeys.index:
            start_journey = veh_journeys.loc[route,'Start_Time_of_Route'] - gv.TIME_INT
            relevant_idx = veh_profile[veh_profile['from'] >= start_journey].index
            for idx in relevant_idx:
                if (
                    (veh_profile.loc[idx,'from'] >= start_journey)
                    & (veh_profile.loc[idx,'from'] < 
                    veh_journeys.loc[(route),'End_Time_of_Route'])):
                    veh_profile.loc[idx,'Available'] = 0
                if (
                    veh_profile.loc[idx,'from'] > veh_journeys.loc[(route),'End_Time_of_Route']
                    - gv.TIME_INT):
                    veh_profile.loc[idx,'Battery_Use'] = -veh_journeys.loc[(route),'Energy_Required']
                    break
        veh_profiles_list.append(veh_profile)
    profiles = pd.concat(veh_profiles_list)
    profiles.sort_values(by=['from','Vehicle_ID'],inplace=True)
    profiles.set_index(['from','Vehicle_ID'],inplace=True)
    # Creates a column to identify a charging session for each vehicle
    profiles['Session'] = 0
    profiles['Return'] = (profiles['Battery_Use'] != 0).astype(int)
    session_num = 0
    for v in vehicles:
        profiles.loc[(slice(None),v),'Session'] = (
            session_num + profiles.loc[(slice(None),v),'Return'].cumsum())
        session_num = profiles['Session'].max()
    profiles['Session'] = profiles['Session'] * profiles['Available']
    return profiles

def create_daily_schedule(profile, day):
    """Takes a single day from journey data and makes a schedule

    Args:
        profile (DataFrame): profile for a whole range, all vehicles
        day (datetime):

    Returns:
        DataFrame: profile for that day, sorted
    """
    start_datetime = day + gv.CHAR_ST_DELTA
    end_datetime = start_datetime + dt.timedelta(days=1)
    day_profile = profile[(profile.index.get_level_values(0) < end_datetime)
    & (profile.index.get_level_values(0) >= start_datetime)]
    return day_profile.sort_index()

if __name__ == "__main__":
    all_journeys = prep_data(gv.data_path, gv.CATEGORY)
    print('All journeys done')
    journeys_range = get_range_data(all_journeys, gv.DAY, gv.TIME_RANGE)
    print('Range journeys done')
    price_data = clean_pricing(gv.pricing_path)
    print('Prices done')
    script_strt = time.process_time()
    empty_profile = create_empty_schedule(journeys_range, price_data)
    print(time.process_time() - script_strt)
    print('Profiles done')

    # # Pickle
    pickle.dump(all_journeys,open('Outputs/all_journeys','wb'))
    pickle.dump(journeys_range,open('Outputs/journeys_range','wb'))
    pickle.dump(price_data,open('Outputs/price_data','wb'))
    pickle.dump(empty_profile,open('Outputs/empty_profile','wb'))

