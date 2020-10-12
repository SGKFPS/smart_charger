# Functions for EV scheduling

import numpy as np
import global_variables as gv
import pandas as pd
import datetime as dt

# Create a function to get daily data
def get_daily_data(journeys,day):
    if journeys.index.isin([day.date()],level='date').any():
        daily_df = journeys.loc[(day)].copy()
        daily_df.drop(columns=['Branch_ID'], inplace=True)
        daily_df.sort_values(by=['Start_Time_of_Route'], inplace=True)
    else:
        daily_df = pd.DataFrame(columns=['None'])
    return daily_df

# # Create function for one route, in one day
# def singleroute_BAU_schedule(journeys, day, route, eprice):
#     mask = ( (eprice['from'] >= dt.datetime.combine(day, gv.CHAR_ST)) 
#     & (eprice['from'] < dt.datetime.combine(day + dt.timedelta(days=1), gv.CHAR_ST)))
#     single_profile = eprice[mask][['from','Electricity_Price','Time_Price']].copy()
#     single_profile['Route_ID'] = route
#     single_profile['Vehicle_ID'] = journeys.loc[(day,route)]['Vehicle_ID']
#     return single_profile

# Takes a single day from journey data and makes a schedule
def create_daily_schedule(profile, day):
    start_datetime = day + gv.CHAR_ST_DELTA
    end_datetime = start_datetime + dt.timedelta(days=1)
    day_profile = profile[(profile.index.get_level_values(0) < end_datetime)
    & (profile.index.get_level_values(0) >= start_datetime)]
    return day_profile.sort_index()

# Creates an empty schedule with journey information
def create_empty_schedule(journeys, eprice):
    """Creates a schedule for each vehicle in a range

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
            for idx in veh_profile.index:
                if (
                    (veh_profile.loc[idx,'from'] >= veh_journeys.loc[(route),'Start_Time_of_Route'] - dt.timedelta(minutes=30))
                    & (veh_profile.loc[idx,'from'] < veh_journeys.loc[(route),'End_Time_of_Route'])):
                    veh_profile.loc[idx,'Available'] = 0
                if veh_profile.loc[idx,'from'] > veh_journeys.loc[(route),'End_Time_of_Route'] - dt.timedelta(minutes=30):
                    veh_profile.loc[idx,'Battery_Use'] = -veh_journeys.loc[(route),'Energy_Required']
                    break
        veh_profiles_list.append(veh_profile)
    profiles = pd.concat(veh_profiles_list)
    profiles.sort_values(by=['from','Vehicle_ID'],inplace=True)
    profiles.set_index(['from','Vehicle_ID'],inplace=True)
    return profiles

# Creates the timeline for a given day with the price information
def create_day_times(day,eprice):
    mask = ( (eprice['from'] >= dt.datetime.combine(day, gv.CHAR_ST)) 
    & (eprice['from'] < dt.datetime.combine(day + dt.timedelta(days=1), gv.CHAR_ST)))
    timeline = eprice[mask][['from','Electricity_Price','Time_Price']].copy()
    timeline['date'] = day
    return timeline

# Creates the timeline for a given day with the price information
def create_range_times(time_range,eprice):
    mask = ( (eprice['from'] >= time_range[0]) 
    & (eprice['from'] < time_range[1]))
    timeline = eprice[mask][['from','Electricity_Price','Time_Price']].copy()
    timeline['date'] = pd.to_datetime((timeline['from'] - gv.CHAR_ST_DELTA).dt.date)
    return timeline