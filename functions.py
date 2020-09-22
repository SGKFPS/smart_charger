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

# Create function for one route, in one day
def singleroute_BAU_schedule(journeys, day, route, eprice):
    mask = ( (eprice['from'] >= dt.datetime.combine(day, gv.CHAR_ST)) 
    & (eprice['from'] < dt.datetime.combine(day + dt.timedelta(days=1), gv.CHAR_ST)))
    single_profile = eprice[mask][['from','Electricity_Price','Time_Price']].copy()
    single_profile['Route_ID'] = route
    single_profile['Vehicle_ID'] = journeys.loc[(day,route)]['Vehicle_ID']
    return single_profile

# Takes a single day from journey data and makes a schedule
def create_daily_schedule(profile, day):
    start_datetime = day + gv.CHAR_ST_DELTA
    end_datetime = start_datetime + dt.timedelta(days=1)
    day_profile = profile[(profile.index.get_level_values(0) < end_datetime)
    & (profile.index.get_level_values(0) >= start_datetime)]
    return day_profile.sort_index()

# Creates an empty schedule with journey information
def create_empty_schedule(journeys, eprice):
    start_range = dt.datetime.combine(min(
        journeys.index.get_level_values('date').date), 
        gv.CHAR_ST)
    end_range = dt.datetime.combine(max(
        journeys.index.get_level_values('date').date), 
        gv.CHAR_ST)
    time_range = [start_range, end_range]
    # Iterate over each day
    dates = journeys.index.unique(level='date')
    # print(dates)
    days_profile = {}

    for date in dates:
        print(date)
        day = date.to_pydatetime()
        if day.date() == time_range[1].date():
            break
        # Create a simple timeline with price info for that day
        day_timeline = create_day_times(day, eprice)
        # Iterate over vehicles and create df
        day_journeys = journeys.loc[day]
        vehicles = day_journeys['Vehicle_ID'].unique()
        veh_profiles_list = []
        for vehicle in vehicles:
            veh_profile = create_day_times(
                day,
                eprice
            )
            veh_profile['Vehicle_ID'] = vehicle
            veh_profile['Available'] = 1
            veh_profile['Battery_Use'] = 0
            # Get journeys for that vehicle that day
            veh_journeys = day_journeys[day_journeys['Vehicle_ID'] == vehicle]
            veh_journeys = veh_journeys.sort_values(by='Start_Time_of_Route')

            #Get next day departure:
            last_departure = veh_journeys.iloc[-1]['Next_Departure']

            for route in veh_journeys.index.get_level_values(0):
                for idx in veh_profile.index:
                    if (
                        (veh_profile.loc[idx,'from'] >= veh_journeys.loc[(route),'Start_Time_of_Route'] - dt.timedelta(minutes=30))
                        & (veh_profile.loc[idx,'from'] < veh_journeys.loc[(route),'End_Time_of_Route'])):
                        veh_profile.loc[idx,'Available'] = 0
                    elif (veh_profile.loc[idx,'from'] >= last_departure - dt.timedelta(minutes=30)):
                        veh_profile.loc[idx,'Available'] = 0
                for idx in veh_profile.index:
                    if veh_profile.loc[idx,'from'] > veh_journeys.loc[(route),'End_Time_of_Route'] - dt.timedelta(minutes=30):
                        veh_profile.loc[idx,'Battery_Use'] = -veh_journeys.loc[(route),'Energy_Required']
                        break
            veh_profiles_list.append(veh_profile)
        days_profile[day] = pd.concat(veh_profiles_list)
    profiles = pd.concat(list(days_profile.values()))
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
