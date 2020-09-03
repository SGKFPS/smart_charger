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
    charging_profile = eprice[range_mask]
    charging_profile.reset_index(inplace=True, drop=True)
    return charging_profile, [start_range, end_range]

def dumb_charging(journeys, eprice):
    # In 100% charge mode, every night we recharge the 'Required_SOC' of that day
    journeys['Time_to_charge'] = journeys['Required_SOC'] / gv.CHARGER_POWER
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
    return profiles

# Create function for one vehicle, in one day
def single_BAU_schedule(journeys, day, vehicle, eprice):
    return_time = journeys.loc[(day, vehicle),'End_Time_of_Route']
    return_datetime = dt.datetime.combine(day, return_time)
    required_charge = journeys.loc[(day, vehicle),'Required_SOC']
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