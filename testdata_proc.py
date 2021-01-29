# Data processing functions for testing optimiser. Phase 2
# Cloned from Phase 1, 26 October 2020
# Sofia Taylor, Flexible Power Systems

import numpy as np
from numpy.core.fromnumeric import shape
import pandas as pd
import datetime as dt
import glob
import pickle
import global_variables as gv
import random
import time


def prep_data_limit(path, category):
    """Preprocess journey data

    Formats datetimes, selects vans, gets next departure/previous arrival

    Args:
        path (str): filepath of journey data
        category (str): 'PROT' or 'TEST'

    Returns:
        DataFrame: table of all journeys
    """
    all_files = glob.glob(path)
    journeys = pd.concat(
        (pd.read_csv(f, usecols=gv.IMPORT_COLS) for f in all_files))
    non_ev = journeys[journeys['vannumber_ev_'] == 0].index
    journeys.drop(non_ev, inplace=True)
    journeys['Start_Time_of_Route'] = pd.to_datetime(
        journeys['Start_Time_of_Route'])
    journeys['date'] = journeys['Start_Time_of_Route'].dt.date
    journeys.rename(columns={'vannumber_ev_': 'Vehicle_ID'}, inplace=True)
    journeys = limit_vehicles_multishift(journeys, category)
    journeys['End_Time_of_Route'] = pd.to_datetime(
        journeys['End_Time_of_Route'])
    journeys = get_prev_arrival(journeys)
    journeys.sort_values(by=['date', 'Route_ID'], inplace=True)
    journeys.set_index(['date', 'Route_ID'], inplace=True)
    return journeys


def prep_data_JLP(path):
    """Preprocess journey data from JLP stores

    Formats datetimes, gets next departure/previous arrival. Journeys
    must be already allocated and individual journeys under battery
    cap.

    Args:
        path (str): filepath of journey data

    Returns:
        DataFrame: table of all journeys
    """
    journeys_all = pd.read_csv(
        path,
        parse_dates=['Start_Date_of_Route', 'Start_Time_of_Route',
                     'End_Time_of_Route'],
        dayfirst=True)
    branches = gv.STORE_SPEC.keys()
    journeys_all['date'] = pd.to_datetime(
        journeys_all['Start_Date_of_Route']).dt.date
    journeys_all['Start_Time_of_Route'] = (
        journeys_all['Start_Time_of_Route'] - dt.datetime(1900, 1, 1))
    journeys_all['Start_Time_of_Route'] = (
        journeys_all['Start_Time_of_Route']
        + journeys_all['Start_Date_of_Route'])
    journeys_all['End_Time_of_Route'] = (
        journeys_all['End_Time_of_Route'] - dt.datetime(1900, 1, 1))
    journeys_all['End_Time_of_Route'] = (
        journeys_all['End_Time_of_Route']
        + journeys_all['Start_Date_of_Route'])
    journeys_all['Route_Time'] = (
        journeys_all['End_Time_of_Route']
        - journeys_all['Start_Time_of_Route']).dt.total_seconds()/3600

    jour = {}
    for branch in branches:
        jour[branch] = journeys_all[journeys_all['Branch_ID'] == branch]
        jour[branch] = get_prev_arrival(jour[branch])
        jour[branch].sort_values(by=['date', 'Route_ID'], inplace=True)
        jour[branch].set_index(['date', 'Route_ID'], inplace=True)
        jour[branch]['Energy_Required'] = (
            jour[branch]['Planned_total_Mileage']
            * gv.VSPEC[gv.STORE_SPEC[branch]['V']]['D']
            + jour[branch]['Route_Time']*gv.REF_CONS)
    journeys = pd.concat(jour)
    return journeys


def prep_data_mixed(path, vs, ch, dates, vNum):
    """Preprocess journey data from JLP stores with a mixed fleet

    Formats datetimes, gets next departure/previous arrival. Journeys
    must be already allocated and individual journeys under battery
    cap.

    Args:
        path (str): filepath of journey data
        vs (list): list of vehicles in use
        ch (list): list of chargers in use
        dates (list): list of dates (datetime) in use
        vNum (list): list of (int) number of vehicles of each kind

    Returns:
        DataFrame: table of all journeys
        dict: Vehicle_ID: Vehicle Model
    """
    journeys = pickle.load(open(path, 'rb'))
    journeys['date'] = pd.to_datetime(
        journeys['Start_Date_of_Route']).dt.date
    journeys['Start_Time_of_Route'] = (
        journeys['Start_Time_of_Route'] - dt.datetime(1900, 1, 1))
    journeys['Start_Time_of_Route'] = (
        journeys['Start_Time_of_Route']
        + journeys['Start_Date_of_Route'])
    journeys['End_Time_of_Route'] = (
        journeys['End_Time_of_Route'] - dt.datetime(1900, 1, 1))
    journeys['End_Time_of_Route'] = (
        journeys['End_Time_of_Route']
        + journeys['Start_Date_of_Route'])
    # journeys['Route_Time'] = (
    #     journeys['End_Time_of_Route']
    #     - journeys['Start_Time_of_Route']).dt.total_seconds()/3600
    journeys['Route_Time'] = 0
    journeys = journeys[journeys['Start_Date_of_Route'].isin(dates)]
    vJourneys = (journeys.groupby(['Start_Date_of_Route', 'Vehicle_ID']).agg({
        'Start_Time_of_Route': 'min',
        'End_Time_of_Route': 'max',
        'EqMileage': 'sum',
        'Shift': 'count',
        'Route_Cost': 'max',
        'Loaded_Kgs': 'max'}))
    vJourneys['Van'] = vs[-1]
    vJourneys.loc[vJourneys['Route_Cost'] > 0.5, 'Van'] = vs[0]
    vJourneys.loc[
        (vJourneys['Route_Cost'] == 0)
        & (vJourneys['EqMileage'] <= gv.VSPEC[vs[0]]['R']), 'Van'] = vs[0]
    for date in dates:
        dayJ = vJourneys.loc[date]
        move = max(len(dayJ[dayJ['Van'] == vs[0]]) - vNum[0], 0)
        newLarge = dayJ[dayJ['Van'] == vs[0]].sort_values(
            by='EqMileage', ascending=False).index[:move]
        vJourneys.loc[(date, newLarge), 'Van'] = vs[-1]
        dayJ = vJourneys.loc[date]
        slowidx = dayJ[dayJ['Van'] == vs[0]].index
        fastidx = dayJ[dayJ['Van'] == vs[-1]].index
        vJourneys.loc[(date, slowidx), 'NewVehicleID'] = range(1, len(slowidx)+1)
        vJourneys.loc[(date, fastidx), 'NewVehicleID'] = range(
            vNum[0]+1, vNum[0]+len(fastidx)+1)
    journeys = journeys.merge(vJourneys[['Van', 'NewVehicleID']],
                              left_on=['Start_Date_of_Route', 'Vehicle_ID'],
                              right_index=True)
    journeys = get_prev_arrival(journeys)
    journeys['Old_VID'] = journeys['Vehicle_ID']
    journeys['Vehicle_ID'] = journeys['NewVehicleID']
    journeys.sort_values(by=['date', 'Route_ID'], inplace=True)
    journeys.reset_index(inplace=True)
    journeys.set_index(['date', 'Route_ID'], inplace=True)
    journeys['Energy_Required'] = (
        journeys['Planned_total_Mileage']
        * journeys['Van'].map(gv.VSPEC).apply(pd.Series)['D']
        + journeys['Route_Time'] * gv.REF_CONS)
    journeys.drop(columns=['NewVehicleID', 'Req_Energy'], inplace=True)
    dictV = {i: vs[0] for i in range(1, vNum[0]+1)}
    dictV.update({i: vs[-1] for i in range(vNum[0] + 1, vNum[0] + vNum[-1]+1)})
    return journeys, dictV


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
        # previous_arrival = dt.datetime.combine(
        #     min(journeys['date']),
        #     dt.datetime.min.time())
        # for idx in van_journeys.index:
        #     van_journeys.loc[idx, 'Previous_Arrival'] = previous_arrival
        #     previous_arrival = van_journeys.loc[idx, 'End_Time_of_Route']
        van_journeys_list.append(van_journeys)
    return pd.concat(van_journeys_list)


def remove_busy_routes(journeys):
    """Removes journeys that require more than 100% battery

    Removes one journey at a time from days that go over 100% battery
    capacity per vehicle.

    Args:
        journeys (DataFrame): table of journeys

    Returns:
        DataFrame: cleaned table of journeys
    """
    all_vehicles = journeys.groupby(['date', 'Vehicle_ID']).sum()
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
        all_vehicles = clean_journeys.groupby(['date', 'Vehicle_ID']).sum()
        busy_dates = all_vehicles[
            all_vehicles['Energy_Required'] > gv.BATTERY_CAPACITY
            ].index
    return clean_journeys


def get_range_data(journeys, day, delta):
    """Takes a week worth of data (or some period) from the combined dataframe

    Args:
        journeys (DataFrame): dataframe of all journeys in a given period

    Returns:
        week: dataframe containing only the journeys in that period
    """

    week = journeys[(journeys.index.get_level_values('date') >= day)
                    & (journeys.index.get_level_values('date') < day + delta)]
    return week


def clean_pricing(path):
    """Creates df with electricity and time price

    This produces a list of electricity prices for each time period.
    It also creates a fake increasing 'time price' to use for benchmarking.
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
    pricing.rename(columns={'unit_rate_excl_vat': 'Electricity_Price'},
                   inplace=True)
    return pricing


def BAU_pricing(jour):
    """Creates a df of pricing data just for BAU

    Args:
        journeys (DataFrame): dictionary of journeys

    Returns:
        DataFrame: schedule with fake pricing data
    """
    journeys = pd.concat(jour)
    start_range = dt.datetime.combine(min(
        journeys.index.get_level_values('date').date),
        gv.CHAR_ST)
    end_range = dt.datetime.combine(max(
        journeys.index.get_level_values('date').date),
        gv.CHAR_ST)
    num_tp = int((end_range - start_range).total_seconds()
                 / gv.TIME_INT.total_seconds())
    tps = [start_range + i*gv.TIME_INT for i in range(num_tp)]
    df = pd.DataFrame(columns=['from', 'Time_Price'])
    df['from'] = tps
    df['Time_Price'] = list(range(len(df)))
    df['Time_Price'] = df['Time_Price'] / 1000
    df['Electricity_Price'] = gv.EPRICE
    return df


def clean_JLpricing(path, dates):
    """Creates df with electricity and time price based on JL tariff

    This produces a list of electricity prices for each time period.
    It also creates a fake increasing 'time price' to use for benchmarking.
    Args:
        path (str): filepath of electricity price

    Returns:
        DataFrame: [description]
    """
    minD = dates.min()
    nDays = (dates.max() - minD).days + 2
    pDates = [minD + i*dt.timedelta(days=1) for i in range(nDays)]
    pricing = pd.read_excel(path, sheet_name='Rate Backing',
                            header=2, usecols="L,AA", names=['Time', 'Price'])
    pricing['Time'] = pd.to_timedelta(pricing['Time'].astype(str))
    df = pd.DataFrame({
        'Date': np.repeat(pDates, 48),
        'Time': np.tile(pricing['Time'], len(pDates)),
        'Electricity_Price': np.tile(pricing['Price']*100, len(pDates))})
    df['from'] = df['Date'] + df['Time']
    df['Time_Price'] = list(range(len(df)))
    df['Time_Price'] = df['Time_Price']/1000
    return df


def create_range_times(time_range, eprice):
    """Creates the timeline for a given range with the price information

    Args:
        time_range (list): list of 2 elements: start/end datetime
        eprice (DataFrame): table of electricity price

    Returns:
        DataFrame: dataframe of timeperiods with electricity price
    """
    mask = ((eprice['from'] >= time_range[0])
            & (eprice['from'] < time_range[1]))
    timeline = eprice[mask][[
        'from', 'Electricity_Price', 'Time_Price']].copy()
    timeline['date'] = pd.to_datetime((
        timeline['from'] - gv.CHAR_ST_DELTA).dt.date)
    return timeline


def create_empty_schedule(journeys, eprice):
    """Creates a empty schedule for each vehicle in a range

    Includes journey information as availability, energy consumption
    and electricity price.

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
    end_range = (dt.datetime.combine(end_date.date(), gv.CHAR_ST)
                 + dt.timedelta(days=1))
    time_range = [start_range, end_range]
    num_days = (end_date.date() - start_date.date()).days
    # days_profile = {}
    vehicles = journeys['Vehicle_ID'].unique()
    veh_profiles_list = []
    for vehicle in vehicles:
        veh_profile = create_range_times(time_range, eprice)
        veh_profile['Vehicle_ID'] = vehicle
        veh_profile['Available'] = 1
        veh_profile['Battery_Use'] = 0
        # Get journeys for that vehicle
        veh_journeys = journeys[journeys['Vehicle_ID'] == vehicle].droplevel(
            'date')
        veh_journeys = veh_journeys.sort_values(by='Start_Time_of_Route')

        for route in veh_journeys.index:
            # Assign 0 to availability when vehicle is out
            idx_unav, idx_return = tp_journeys(veh_profile, veh_journeys, route)
            veh_profile.loc[idx_unav, 'Available'] = 0
            # Assign energy used when vehicle returns
            veh_profile.loc[idx_return, 'Battery_Use'] = -veh_journeys.loc[
                        route, 'Energy_Required']
        veh_profiles_list.append(veh_profile)
    #print(veh_profiles_list)
    profiles = pd.concat(veh_profiles_list)
    profiles.sort_values(by=['from', 'Vehicle_ID'], inplace=True)
    profiles.set_index(['from', 'Vehicle_ID'], inplace=True)
    # Creates a column to identify a charging session for each vehicle
    profiles['Session'] = 0
    profiles['Return'] = (profiles['Battery_Use'] != 0).astype(int)
    session_num = 0
    for v in vehicles:
        profiles.loc[(slice(None), v), 'Session'] = (
            session_num + profiles.loc[(slice(None), v), 'Return'].cumsum())
        session_num = profiles['Session'].max()
    profiles['Session'] = profiles['Session'] * profiles['Available']
    return profiles

def setup_inputs(journeys, eprice):
    """Creates a empty schedule for each vehicle in a range

    Includes journey information as availability, energy consumption
    and electricity price.

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
    end_range = (dt.datetime.combine(end_date.date(), gv.CHAR_ST)
                 + dt.timedelta(days=1))
    time_range = [start_range, end_range]
    num_days = (end_date.date() - start_date.date()).days
    # days_profile = {}
    vehicles = journeys['Vehicle_ID'].unique()
    veh_profiles_list = []
    for vehicle in vehicles:
        veh_profile = create_range_times(time_range, eprice)
        veh_profile['Vehicle_ID'] = vehicle
        veh_profile['Available'] = 1
        veh_profile['Battery_Use'] = 0
        # Get journeys for that vehicle
        veh_journeys = journeys[journeys['Vehicle_ID'] == vehicle].droplevel(
            'date')
        veh_journeys = veh_journeys.sort_values(by='Start_Time_of_Route')

        for route in veh_journeys.index:
            # Assign 0 to availability when vehicle is out
            idx_unav, idx_return = tp_journeys(veh_profile, veh_journeys, route)
            veh_profile.loc[idx_unav, 'Available'] = 0
            # Assign energy used when vehicle returns
            veh_profile.loc[idx_return, 'Battery_Use'] = -veh_journeys.loc[
                        route, 'Energy_Required']
        veh_profiles_list.append(veh_profile)
    print(veh_profiles_list[0].columns)
    # profiles = pd.concat(veh_profiles_list)
    # profiles.sort_values(by=['from', 'Vehicle_ID'], inplace=True)
    # profiles.set_index(['from', 'Vehicle_ID'], inplace=True)
    # Creates a column to identify a charging session for each vehicle
    session_num = 0
    for v in veh_profiles_list:
        v['Session'] = 0
        v['Return'] = (v['Battery_Use'] != 0).astype(int)
        v['Session'] = (session_num + v['Return'].cumsum())
        session_num = v['Session'].max()
        v['Session'] = v['Session'] * v['Available']
    return veh_profiles_list

def create_dailys(profile, day):
    """Takes a single day from journey data and makes a schedule

    Args:
        profile (DataFrame): profile for a whole range, all vehicles
        day (datetime):

    Returns:
        DataFrame: profile for that day, sorted
    """
    start_datetime = day + gv.CHAR_ST_DELTA
    end_datetime = start_datetime + dt.timedelta(days=1)

    profiles = pd.concat(profile)
    profiles.sort_values(by=['from', 'Vehicle_ID'], inplace=True)
    profiles.set_index(['from', 'Vehicle_ID'], inplace=True)

    #print(profiles)
    
    day_profile = profiles[(profiles.index.get_level_values(0) < end_datetime)
                          & (profiles.index.get_level_values(0)
                              >= start_datetime)]

    return day_profile.sort_index()


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
                          & (profile.index.get_level_values(0)
                              >= start_datetime)]
    return day_profile.sort_index()

def create_daily(profile, day):
    """Takes a single day from journey data and makes a schedule

    Args:
        profile (DataFrame): profile for a whole range, all vehicles
        day (datetime):

    Returns:
        DataFrame: profile for that day, sorted
    """
    start_datetime = day + gv.CHAR_ST_DELTA
    end_datetime = start_datetime + dt.timedelta(days=1)
    day_profile = [( p[(p['from'] < end_datetime) & (p['from'] >= start_datetime)]).sort_index().reset_index(drop=True) 
                    for p in profile]
    return day_profile


def clean_site_capacityJLP(br, year, path):
    """Creates a df of available capacity for each time period

    Args:
        br (int): branch ID
        year (int): year
        path (str): relative or absolute path of meter data

    Returns
        df: for each tp, other site load and available site capacity
    """
    meter = pd.read_csv(path, usecols=['DateTime', 'kWh'],
                        parse_dates=['DateTime'], dayfirst=True)
    meter['Available_kW'] = gv.STORE_SPEC[br]['ASC'] - meter['kWh']*2
    meter['Available_nolim'] = 20000
    meter.set_index('DateTime', inplace=True)
    return meter


def tp_journeys(profile, journeys, route):
    after_departure = profile['from'] > (
        journeys.loc[route, 'Start_Time_of_Route'] - gv.TIME_INT)
    before_end = profile['from'] < (
        journeys.loc[route, 'End_Time_of_Route'] + gv.IS_LEEWAY)
    before_return = profile['from'] < journeys.loc[route, 'End_Time_of_Route']
    return_idx = profile[before_return]['from'].idxmax()
    return after_departure & before_end, return_idx


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
    pickle.dump(all_journeys, open('Outputs/all_journeys', 'wb'))
    pickle.dump(journeys_range, open('Outputs/journeys_range', 'wb'))
    pickle.dump(price_data, open('Outputs/price_data{}'.format(gv.YEAR), 'wb'))
    pickle.dump(empty_profile, open('Outputs/empty_profile', 'wb'))
