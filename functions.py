# Functions for EV scheduling

import numpy as np
import global_variables as gv
import pandas as pd
import datetime as dt

def create_empty_schedule(journeys, eprice):
    start_range = dt.datetime.combine(min(journeys.index.get_level_values('date').date), gv.CHAR_ST)
    end_range = dt.datetime.combine(max(journeys.index.get_level_values('date').date), gv.CHAR_ST)
    time_span = end_range - start_range
    num_intervals = time_span / gv.TIME_INT
    # Create dataframe with pricing data for that range
    range_mask = ((eprice['from'] >= start_range) & 
                    (eprice['from'] < end_range))
    charging_profile = eprice[range_mask].copy()
    charging_profile.reset_index(inplace=True, drop=True)
    charging_profile.drop(columns=['to'], inplace=True)
    return charging_profile, [start_range, end_range]

def dumb_charging(journeys, eprice):
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
    daily_df = journeys.loc[(day)][['End_Time_of_Route','Energy_Required']]
    daily_df['Start_next_route'] = journeys.loc[(day+dt.timedelta(days=1))]['Start_Time_of_Route']
    return daily_df

# Create function for one vehicle, in one day
def singleveh_BAU_schedule(journeys, day, vehicle, eprice):
    # return_time = journeys.loc[(day, vehicle),'End_Time_of_Route']
    # return_datetime = dt.datetime.combine(day, return_time)
    return_datetime = journeys.loc[(day, vehicle),'End_Time_of_Route']
    required_charge = journeys.loc[(day, vehicle),'Energy_Required']
    # depart_time = journeys.loc[(day + dt.timedelta(days=1), vehicle),'Start_Time_of_Route']
    # depart_datetime = dt.datetime.combine(day + dt.timedelta(days=1), depart_time)
    #print(depart_datetime)
    #print('Return:', return_datetime, "\nDepart:", depart_datetime, '\nRequired charge:', required_charge)
    mask = ( (eprice['from'] >= dt.datetime.combine(day, gv.CHAR_ST)) 
    & (eprice['from'] < dt.datetime.combine(day + dt.timedelta(days=1), gv.CHAR_ST)))
    single_profile = eprice[mask][['from','unit_rate_excl_vat']].copy()
    timesidx = single_profile.index
    single_profile['Output_BAU'] = 0
    single_profile['SOC_BAU'] = gv.BATTERY_CAPACITY - required_charge
    prev_idx = timesidx[0]
    for idx in timesidx:
        if single_profile.loc[idx,'from']  <= return_datetime:
            single_profile.loc[idx,'Output_BAU'] = 0
        elif gv.BATTERY_CAPACITY - single_profile.loc[prev_idx,'SOC_BAU'] > gv.CHARGER_POWER/2:
            single_profile.loc[idx,'Output_BAU'] = gv.CHARGER_POWER / 2 #FIXME generalise for any time interval
        elif gv.BATTERY_CAPACITY - single_profile.loc[prev_idx,'SOC_BAU'] > 0:
            single_profile.loc[idx,'Output_BAU'] = gv.BATTERY_CAPACITY - single_profile.loc[prev_idx,'SOC_BAU']
        single_profile.loc[idx,'SOC_BAU'] = gv.BATTERY_CAPACITY - required_charge + single_profile['Output_BAU'].sum() * gv.CHARGER_EFF
        prev_idx = idx  
    single_profile['Vehicle'] = vehicle    
    return single_profile

    # Create second BAU scheduling function that uses multi index

def BAU_charging(journeys, eprice):
    # Create df for charge profile, with time slots in that time range. 
    _, time_range = create_empty_schedule(journeys, eprice)
    # Iterate over each day
    dates = journeys.index.unique(level='date')
    print(dates)
    day_profile = {}
    for date in dates:
        day = date.to_pydatetime()
        if day.date() == time_range[1].date():
            break
        # Iterate over vehicles, copy to correct column
        vehicle_profiles = {}
        for vehicle in range(gv.NUM_VEHICLES):
            vehicle_profiles[vehicle] = singleveh_BAU_schedule(journeys, day, vehicle, eprice)
        day_profile[day] = pd.concat(list(vehicle_profiles.values()))
    profiles = pd.concat(list(day_profile.values()))
    profiles.sort_values(by=['from','Vehicle'],inplace=True)
    profiles.set_index(['from','Vehicle'],inplace=True)
    return profiles

# Takes a single day from BAU
def create_daily_schedule(journeys, day):
    start_datetime = day + gv.CHAR_ST_DELTA
    end_datetime = start_datetime + dt.timedelta(days=1)
    day_profile = journeys[(journeys.index.get_level_values(0) < end_datetime)
    & (journeys.index.get_level_values(0) >= start_datetime)][['Output_BAU','unit_rate_excl_vat']]
    return day_profile

# Creates summary columns and dataframes from outputs
def summary_outputs(profile, journeys):
    vehicles = journeys.index
    day_profile = profile.copy()
    day_profile['Charge_Delivered_Opt'] = day_profile['Output_Opt'] * gv.CHARGER_EFF
    day_profile['Charge_Delivered_BAU'] = day_profile['Output_BAU'] * gv.CHARGER_EFF
    day_profile['Electricity_Cost_Opt'] = day_profile['Output_Opt'] * day_profile['unit_rate_excl_vat']
    day_profile['Electricity_Cost_BAU'] = day_profile['Output_BAU'] * day_profile['unit_rate_excl_vat']
    for vehicle in vehicles:
        opt_soc = (gv.BATTERY_CAPACITY - journeys.loc[vehicle,'Energy_Required'] + day_profile.loc[(slice(None),vehicle),'Charge_Delivered_Opt'].cumsum())*100 / gv.BATTERY_CAPACITY
        day_profile.loc[(slice(None),vehicle),'SOC_Opt'] = opt_soc
        opt_BAU = (gv.BATTERY_CAPACITY - journeys.loc[vehicle,'Energy_Required'] + day_profile.loc[(slice(None),vehicle),'Charge_Delivered_BAU'].cumsum())*100 / gv.BATTERY_CAPACITY
        day_profile.loc[(slice(None),vehicle),'SOC_BAU'] = opt_BAU

    day_journeys = journeys.copy()
    day_journeys['Energy_Use_Opt'] = day_profile['Output_Opt'].groupby(level=1).sum()
    day_journeys['Energy_Use_BAU'] = day_profile['Output_BAU'].groupby(level=1).sum()
    day_journeys['Electricity_Cost_Opt'] = day_profile['Electricity_Cost_Opt'].groupby(level=1).sum()
    day_journeys['Electricity_Cost_BAU'] = day_profile['Electricity_Cost_BAU'].groupby(level=1).sum()
    day_journeys['Peak_Output_Opt'] = day_profile['Output_Opt'].groupby(level=1).max()
    day_journeys['Peak_Output_BAU'] = day_profile['Output_BAU'].groupby(level=1).max()

    site = day_profile.groupby(level=0).sum()
    site['unit_rate_excl_vat'] = site['unit_rate_excl_vat']/gv.NUM_VEHICLES
    site['SOC_Opt'] = site['SOC_Opt']/gv.NUM_VEHICLES
    site['SOC_BAU'] = site['SOC_BAU']/gv.NUM_VEHICLES

    global_summary = site.sum()
    global_summary.drop(labels=['unit_rate_excl_vat','SOC_Opt','SOC_BAU'], inplace=True)
    return day_profile, day_journeys, site, global_summary
