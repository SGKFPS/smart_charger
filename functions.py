# Functions for EV scheduling

import numpy as np
import global_variables as gv
import pandas as pd
import datetime as dt

def create_empty_schedule(journeys, eprice):
    start_range = dt.datetime.combine(min(journeys.index.get_level_values('date').date), gv.CHAR_ST)
    end_range = dt.datetime.combine(max(journeys.index.get_level_values('date').date), gv.CHAR_ST)
    time_range = [start_range, end_range]
    # Iterate over each day
    dates = journeys.index.unique(level='date')
    # print(dates)
    day_profile = {}
    vehicles = journeys['Vehicle_ID'].unique()
    for date in dates:
        day = date.to_pydatetime()
        if day.date() == time_range[1].date():
            break
        # Iterate over routes, copy to correct column
        route_profiles = {}
        for route in journeys.loc[day].index:
            route_profiles[route] = singleroute_BAU_schedule(
                journeys, 
                day, 
                route, 
                eprice)
        day_profile[day] = pd.concat(list(route_profiles.values()))
    profiles = pd.concat(list(day_profile.values()))
    profiles.sort_values(by=['from','Route_ID'],inplace=True)
    profiles.set_index(['from','Route_ID'],inplace=True)
    return profiles

def dumb_charging_no(journeys, eprice): # TODO am I using this?
    # Create df for charge profile, with time slots in that time range. 
    empty_profile, time_range = create_empty_schedule(journeys, eprice)
    # Iterate over each day
    dates = journeys.index.unique(level='date')
    day_profile = {}
    for date in dates:
        day = date.to_pydatetime()
        if day.date() == time_range[1].date():
            break
        day_profile[day] = empty_profile.copy()
        # Get section of profile that fits the day
        # Iterate over vehicles, copy to correct column
        for vehicle in range(gv.NUM_VEHICLES):
            day_profile[day] = day_profile[day].merge(
                single_BAU_schedule(journeys,day,vehicle,eprice[['from']]),
                on = 'from'
            )
    profiles = pd.concat(list(day_profile.values()))
    profiles['Site_output'] = profiles[gv.Power_output.values()].sum(axis=1)
    profiles['Electricity_costs'] = profiles['Site_output'] * profiles['unit_rate_excl_vat']
    return profiles

# Create function for one vehicle, in one day
def single_BAU_schedule(journeys, day, vehicle, eprice):
    return_time = journeys.loc[(day, vehicle),'End_Time_of_Route']
    return_datetime = dt.datetime.combine(day, return_time)
    required_charge = journeys.loc[(day, vehicle),'Energy_Required']
    depart_time = journeys.loc[(day + dt.timedelta(days=1), vehicle),'Start_Time_of_Route']
    depart_datetime = dt.datetime.combine(day + dt.timedelta(days=1), depart_time)
    #print(depart_datetime)
    #print('Return:', return_datetime, "\nDepart:", depart_datetime, '\nRequired charge:', required_charge)
    mask = ( (eprice['from'] >= dt.datetime.combine(day, gv.CHAR_ST)) 
    & (eprice['from'] < dt.datetime.combine(day + dt.timedelta(days=1), gv.CHAR_ST)))
    single_profile = eprice[mask].copy()
    timesidx = single_profile.index
    single_profile[gv.Power_output[vehicle]] = 0
    single_profile[gv.SOC[vehicle]] = gv.BATTERY_CAPACITY - required_charge
    prev_idx = timesidx[0]
    for idx in timesidx:
        if single_profile.loc[idx,'from'] + gv.TIME_INT <= return_datetime:
            single_profile.loc[idx,gv.Power_output[vehicle]] = 0
        elif single_profile.loc[idx,'from'] <= return_datetime:
            time_charging = (return_datetime - single_profile.loc[idx,'from']).total_seconds()
            single_profile.loc[idx,gv.Power_output[vehicle]] = time_charging * 3.5 / (gv.TIME_INT.total_seconds())
        elif gv.BATTERY_CAPACITY - single_profile.loc[prev_idx,gv.SOC[vehicle]] > gv.CHARGER_POWER/2:
            single_profile.loc[idx,gv.Power_output[vehicle]] = gv.CHARGER_POWER / 2 #FIXME generalise for any time interval
        elif gv.BATTERY_CAPACITY - single_profile.loc[prev_idx,gv.SOC[vehicle]] > 0:
            single_profile.loc[idx,gv.Power_output[vehicle]] = gv.BATTERY_CAPACITY - single_profile.loc[prev_idx,gv.SOC[vehicle]]
        single_profile.loc[idx,gv.SOC[vehicle]] = gv.BATTERY_CAPACITY - required_charge + single_profile[gv.Power_output[vehicle]].sum()
        prev_idx = idx  # FIXME initialise this earlier
    return single_profile
    
# Get list of times in a day
def create_timelist(): #FIXME so that it's always a numpy array
    intervals = int(dt.timedelta(days=1) / gv.TIME_INT)
    time_array = [gv.CHAR_ST_DELTA] * intervals
    for i in range(intervals):
        time_array[i] += gv.TIME_INT * i
    return np.asarray(time_array)

# Create a function to get daily data
def get_daily_data(journeys,day):
    daily_df = journeys.loc[(day)].copy()
    daily_df.drop(columns=['Branch_ID'], inplace=True)
    daily_df.sort_values(by=['Start_Time_of_Route'], inplace=True)
    return daily_df

# Create function for one route, in one day
def singleroute_BAU_schedule(journeys, day, route, eprice):
    mask = ( (eprice['from'] >= dt.datetime.combine(day, gv.CHAR_ST)) 
    & (eprice['from'] < dt.datetime.combine(day + dt.timedelta(days=1), gv.CHAR_ST)))
    single_profile = eprice[mask][['from','Electricity_Price','Time_Price']].copy()
    single_profile['Route_ID'] = route
    single_profile['Vehicle_ID'] = journeys.loc[(day,route)]['Vehicle_ID']
    return single_profile

# Takes a single day from BAU
def create_daily_schedule(journeys, day):
    start_datetime = day + gv.CHAR_ST_DELTA
    end_datetime = start_datetime + dt.timedelta(days=1)
    day_profile = journeys[(journeys.index.get_level_values(0) < end_datetime)
    & (journeys.index.get_level_values(0) >= start_datetime)][[
        'Electricity_Price',
        'Time_Price',
        'Vehicle_ID'
        ]]
    day_profile.sort_index(inplace=True)
    return day_profile