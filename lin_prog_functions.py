# Stores all prototypoe linear_optimiser functions

import numpy as np
import global_variables as gv
import pandas as pd
import datetime as dt
from pulp import *
import functions as f
import time

def linear_optimiser_V1(profile,journeys,ca,charger,capacity):
    price_col = gv.CAT_COLS['PRICE'][ca]
    output_col = gv.CAT_COLS['OUTPUT'][ca]
    # Define output variable
    outputs = LpVariable.dicts("output",
    ((period, route) for period, route in profile.index),
    lowBound = 0,
    upBound = charger * gv.TIME_FRACT,
    cat = "Continuous"
    )

    # Create the 'prob' variable to contain the problem data
    prob = LpProblem("Multiple_route_scheduling",LpMinimize)

    # Add costs to objective function

    prob += lpSum(
        [profile.loc[(period, route), price_col] * outputs[period, route] 
        for period, route in profile.index]
        ), "Total Charging costs"

    # Final SOC constraint
    time_period = profile.index.get_level_values(0)
    routes = profile.index.get_level_values(1)
    vehicles = journeys['Vehicle_ID'].unique()

    for vehicle in vehicles:
        vehicle_profile = profile[profile['Vehicle_ID'] == vehicle]
        prob += lpSum(
            [outputs[period, route] for period, route in vehicle_profile.index]
            ) == (journeys[journeys['Vehicle_ID'] == vehicle]['Energy_Required'].sum() 
            / gv.CHARGER_EFF)

    # Output after/before departure/arrival is 0

    for period, route in profile.index:
        arrival = journeys.loc[route, "End_Time_of_Route"]
        departure = journeys.loc[route, "Next_Departure"]
        if period < arrival:
            prob += outputs[(period, route)] == 0
        elif period + dt.timedelta(minutes=30) > departure:
            prob += outputs[period, route] == 0

    # Max capacity constraint
    n = len(time_period.unique())
    for period in time_period:
        prob += lpSum(
            [outputs[period, route] for route in routes])/n <= capacity[ca]
    
    # Solve and print to the screen
    prob.solve()
    #print(ca, "status:", LpStatus[prob.status])
    # Get output variables
    charge_output = []
    for period, route in outputs:
        if prob.status == 1:
            x =  outputs[(period, route)].varValue
        else:
            x = 0
        var_output = {
            'from': period,
            'Route_ID': route,
            output_col: x
        }
        charge_output.append(var_output)

    df = pd.DataFrame.from_records(charge_output).sort_values(['from','Route_ID'])
    df.set_index(['from', 'Route_ID'], inplace=True)
    #print('Cost:', value(prob.objective))
    return df, prob

# Optimise over a whole range
def optimise_range(empty_profile, charger, capacity):
    dates = np.unique(empty_profile.index.get_level_values(0).date)
    #dates = np.delete(dates,-1)
    all_days_profile = []
    dates_status = ''
    bad_days = 'Bad days:\n'
    status = 0
    for date in dates:
        day_status = 0
        start = time.process_time()
        day = dt.datetime.combine(date, dt.datetime.min.time())
        #day_journeys = f.get_daily_data(journeys, day)
        day_profile = f.create_daily_schedule(empty_profile, day)
        if len(day_profile)==0:
            bad_days += '\nEmpty day:'
            bad_days += str(date)
            pass
        else:
            output_df = {}
            PuLP_prob = {}
            day_profile_out = day_profile.copy()
            for ca in gv.CATS:
                output_df[ca], PuLP_prob[ca] = linear_optimiser_V2(
                    day_profile,
                    ca,
                    charger,
                    capacity
                    )
                day_profile_out = day_profile_out.merge(
                output_df[ca],
                how='left',
                left_index=True,
                right_index=True,
                )
                day_profile_out.fillna(0,inplace=True)
                day_status += PuLP_prob[ca].status
            
            print(
                date,
            #     '\nTime:', time.process_time() - start,
                'Status:',day_status, 
                ':', PuLP_prob['opt'].status, 
                PuLP_prob['BAU'].status,
                PuLP_prob['BAU2'].status)
            #     '\nCost:', value(PuLP_prob['opt'].objective))
            all_days_profile.append(day_profile_out)
            if day_status <3:
                bad_days += '\nNon-Optimal: '
                bad_days += str(date)
                for ca in gv.CATS:
                    bad_days += '_'
                    bad_days += str(PuLP_prob[ca].status)
            dates_status += str([date,day_status])
            dates_status += '\n'

    profile_out = pd.concat(all_days_profile)
    return profile_out, dates, bad_days, PuLP_prob

# Inlcudes SOC constraints
def linear_optimiser_V2(profile,ca,charger,capacity):
    profile_av = profile[profile['Available'] == 1]
    price_col = gv.CAT_COLS['PRICE'][ca]
    output_col = gv.CAT_COLS['OUTPUT'][ca]
    soc_col = gv.CAT_COLS['SOC'][ca]
    vehicles = profile.index.get_level_values(1).unique()
    time_periods = profile_av.index.get_level_values(0).unique()
    # Define output variable
    outputs = LpVariable.dicts(
        "output",
        ((period, vehicle) for period, vehicle in profile_av.index),
        lowBound = 0,
        upBound = charger * gv.TIME_FRACT,
        cat = "Continuous"
        )

    # Create the 'prob' variable to contain the problem data
    prob = LpProblem("Multiple_route_scheduling",LpMinimize)

    # Add costs to objective function

    prob += lpSum(
        [profile_av.loc[(period, vehicle), price_col] * outputs[period, vehicle] 
        for period, vehicle in profile_av.index]
        ), "Total Charging costs"

    # Final SOC constraint
    for vehicle in vehicles:
        vehicle_prof = profile_av.loc[(slice(None),vehicle),'Battery_Use']
        prob += lpSum(
            [outputs[period,vehicle] * gv.CHARGER_EFF for period, vehicle in vehicle_prof.index]
        ) == - profile.loc[(slice(None),vehicle),'Battery_Use'].sum()

    # Intermediate SOC constraints
    for vehicle in vehicles:
        vehicle_prof = profile_av.loc[(slice(None),vehicle),'Battery_Use']
        for period in vehicle_prof.index.get_level_values(0):
            cumul_use = profile.loc[(slice(period),vehicle),'Battery_Use'].sum()
            cumul_profile = profile_av.loc[(slice(period),vehicle),'Battery_Use']
            prob += lpSum(
                [outputs[period, vehicle] * gv.CHARGER_EFF for period, vehicle in cumul_profile.index]
            ) + cumul_use <= 0
            prob += lpSum(
                [outputs[period, vehicle] * gv.CHARGER_EFF for period, vehicle in cumul_profile.index]
            ) + cumul_use >= -gv.BATTERY_CAPACITY + charger * gv.TIME_FRACT

    # Max capacity constraint
    n = len(time_periods.unique())
    for period in time_periods:
        time_routes = list(profile_av.loc[period].index)
        prob += lpSum(
            [outputs[period, route] for route in time_routes]) <= capacity[ca]* gv.TIME_FRACT

    # Solve and print to the screen
    prob.solve()
    print(ca, "status:", LpStatus[prob.status])
    # Get output variables
    charge_output = []
    for period, route in outputs:
        if prob.status == 1:
            x =  outputs[(period, route)].varValue
        else:
            x = 0
        var_output = {
            'from': period,
            'Vehicle_ID': route,
            output_col: x
        }
        charge_output.append(var_output)

    df = pd.DataFrame.from_records(charge_output).sort_values(['from','Vehicle_ID'])
    df.set_index(['from', 'Vehicle_ID'], inplace=True)
    print('Cost:', value(prob.objective))
    return df, prob

# Optimise over a whole range
def optimise_range2(empty_profile, charger, capacity):
    """Linear optimisation for a range of dates

    Creates an output for each time period over a range of dates. Runs a linear
    optimisation over each day independently, passing the final SOC to the next day.

    Args:
        empty_profile (DataFrame): MultiIndex profile of each vehicle / time period
        charger (int): charger power
        capacity (int): max allowed site capacity

    Returns:
        DataFrame: power outputs for each vehicle / time period
        Array: list of dates in the time period
        String: list of dates when optimisation is unfeasible or there are no journeys
        LpProblem: includes all the optimisation information
    """
    dates = np.unique(empty_profile.index.get_level_values(0).date)
    #dates = np.delete(dates,-1)
    all_days_profile = []
    dates_status = ''
    bad_days = 'Bad days:\n'
    status = 0
    initial_rel_charge = pd.Series(
        data = [0,0,0,0,0],
        index = empty_profile.index.get_level_values(1).unique()
    )
    rel_charge = dict.fromkeys(gv.CATS,initial_rel_charge)

    for date in dates:
        day_status = 0
        start = time.process_time()
        day = dt.datetime.combine(date, dt.datetime.min.time())
        day_profile = f.create_daily_schedule(empty_profile, day)
        if len(day_profile)==0:
            bad_days += '\nEmpty day:'
            bad_days += str(date)
            pass
        else:
            output_df = {}
            PuLP_prob = {}
            day_profile_out = day_profile.copy()
            for ca in gv.CATS:
                output_df[ca], PuLP_prob[ca], rel_charge[ca] = linear_optimiser_V3(
                    day_profile,
                    ca,
                    charger,
                    capacity,
                    rel_charge[ca]
                    )
                day_profile_out = day_profile_out.merge(
                    output_df[ca],
                    how='left',
                    left_index=True,
                    right_index=True,
                    )
                day_profile_out.fillna(0,inplace=True)
                day_status += PuLP_prob[ca].status
            
            print(
                date,
            #     '\nTime:', time.process_time() - start,
                'Status:',day_status, 
                ':', PuLP_prob['opt'].status, 
                PuLP_prob['BAU'].status,
                PuLP_prob['BAU2'].status)
            #     '\nCost:', value(PuLP_prob['opt'].objective))
            all_days_profile.append(day_profile_out)
            if day_status <3:
                bad_days += '\nNon-Optimal: '
                bad_days += str(date)
                for ca in gv.CATS:
                    bad_days += '_'
                    bad_days += str(PuLP_prob[ca].status)
            dates_status += str([date,day_status])
            dates_status += '\n'

    profile_out = pd.concat(all_days_profile)
    return profile_out, dates, bad_days, PuLP_prob

# Passes incomplete SoC to next day
def linear_optimiser_V3(profile,ca,charger,capacity,rel_charge):
    """Linear optimisation for a single day charging

    This optimiser uses PuLP to find optimal power outputs over a day.
    Objective: reduce overall electricity spend
    Constraint 1: get to 100% final SOC before end of time period of next day departures
    Constraint 2: not go below 0% or over 100% battery charge
    Constraint 3: not go over site capacity
    If this is unfeasible, it will atempt to charge as much as possible using
    incomplete_charge.

    Args:
        profile (DataFrame): empty profile of a single day
        ca (str): category to use in optimisation (opt, BAU)
        charger (int): charger power
        capacity (int): max allowed site capacity
        rel_charge (Series): list of intial battery charge state relative to full. 
            Index are Vehicle_ID

    Returns:
        [type]: [description]
    """
    profile_av = profile[profile['Available'] == 1]
    price_col = gv.CAT_COLS['PRICE'][ca]
    output_col = gv.CAT_COLS['OUTPUT'][ca]
    vehicles = profile.index.get_level_values(1).unique()
    time_periods = profile_av.index.get_level_values(0).unique()
    # Define output variable
    outputs = LpVariable.dicts(
        "output",
        ((period, vehicle) for period, vehicle in profile_av.index),
        lowBound = 0,
        upBound = charger * gv.TIME_FRACT,
        cat = "Continuous"
        )

    # Create the 'prob' variable to contain the problem data
    prob = LpProblem("Multiple_route_scheduling",LpMinimize)

    # Add costs to objective function
    prob += lpSum(
        [profile_av.loc[(period, vehicle), price_col] * outputs[period, vehicle] 
        for period, vehicle in profile_av.index]
        ), "Total Charging costs"

    # Final SOC constraint
    for vehicle in vehicles:
        vehicle_prof = profile_av.loc[(slice(None),vehicle),'Battery_Use']
        prob += lpSum(
            [outputs[period,vehicle] * gv.CHARGER_EFF for period, vehicle in vehicle_prof.index]
        ) == - (
            profile.loc[(slice(None),vehicle),'Battery_Use'].sum()
            + rel_charge[vehicle]
        )

    # Intermediate SOC constraints
    for vehicle in vehicles:
        vehicle_prof = profile_av.loc[(slice(None),vehicle),'Battery_Use']
        for period in vehicle_prof.index.get_level_values(0):
            cumul_use = profile.loc[(slice(period),vehicle),'Battery_Use'].sum()
            cumul_profile = profile_av.loc[(slice(period),vehicle),'Battery_Use']
            prob += lpSum( # Doesn't go over 100% SOC
                [outputs[period, vehicle] * gv.CHARGER_EFF for period, vehicle in cumul_profile.index]
            ) + cumul_use + rel_charge[vehicle]<= 0
            prob += lpSum( # Doesn't go below 0% SOC
                [outputs[period, vehicle] * gv.CHARGER_EFF for period, vehicle in cumul_profile.index]
            ) + cumul_use + rel_charge[vehicle]>= -gv.BATTERY_CAPACITY + charger * gv.TIME_FRACT

    # Max capacity constraint
    n = len(time_periods.unique())
    for period in time_periods:
        time_routes = list(profile_av.loc[period].index)
        prob += lpSum(
            [outputs[period, route] for route in time_routes]) <= capacity[ca]* gv.TIME_FRACT

    # Solve and print to the screen
    prob.solve()
    print(ca, "status:", LpStatus[prob.status])
    # If unfeasible, tries to 
    if  prob.status == -1:
        df = charge_incomplete(profile,ca,charger,capacity,rel_charge)
    else:
        # Get output variables
        charge_output = []
        for period, route in outputs:
            if prob.status == 1:
                x =  outputs[(period, route)].varValue
            else:
                x = 0
            var_output = {
                'from': period,
                'Vehicle_ID': route,
                output_col: x
            }
            charge_output.append(var_output)

        df = pd.DataFrame.from_records(charge_output).sort_values(['from','Vehicle_ID'])
        df.set_index(['from', 'Vehicle_ID'], inplace=True)
        print('Cost:', value(prob.objective))
    # Generate a final SoC array
    #final_soc = initial_soc
    final_soc = rel_charge + (
        df.groupby('Vehicle_ID').sum()[output_col]*gv.CHARGER_EFF
        + profile.groupby('Vehicle_ID').sum()['Battery_Use'] )
    return df, prob, final_soc

# Incomplete charging when 100% unfeasible
def charge_incomplete(profile,ca,charger,capacity,rel_charge):
    """Optimise charging when 100% is unfeasible
    
    The objective of this function is to deliver as much charge as possible
    without accounting for required final SOC. If this is unfeasible, it will go 
    to magic charging

    Args:
        profile (DataFrame): empty profile of a single day
        ca (str): category to use in optimisation (opt, BAU)
        charger (int): charger power
        capacity (int): max allowed site capacity
        rel_charge (Series): list of intial battery charge state relative to full. 
            Index are Vehicle_ID

    Returns:
        DataFrame: outputs per time period
    """
    profile_av = profile[profile['Available'] == 1]
    price_col = gv.CAT_COLS['PRICE'][ca]
    output_col = gv.CAT_COLS['OUTPUT'][ca]
    vehicles = profile.index.get_level_values(1).unique()
    time_periods = profile_av.index.get_level_values(0).unique()
    # Define output variable
    outputs = LpVariable.dicts(
        "output",
        ((period, vehicle) for period, vehicle in profile_av.index),
        lowBound = 0,
        upBound = charger * gv.TIME_FRACT,
        cat = "Continuous"
        )

    # Create the 'prob' variable to contain the problem data
    prob = LpProblem("Multiple_route_scheduling",LpMaximize)

    # Add costs to objective function
    prob += lpSum(
        [outputs[period, vehicle] for period, vehicle in profile_av.index]
        ), "Total Charging"

    # Intermediate SOC constraints
    for vehicle in vehicles:
        vehicle_prof = profile_av.loc[(slice(None),vehicle),'Battery_Use']
        for period in vehicle_prof.index.get_level_values(0):
            cumul_use = profile.loc[(slice(period),vehicle),'Battery_Use'].sum()
            cumul_profile = profile_av.loc[(slice(period),vehicle),'Battery_Use']
            prob += lpSum( # Doesn't go over 100% SOC
                [outputs[period, vehicle] * gv.CHARGER_EFF for period, vehicle in cumul_profile.index]
            ) + cumul_use + rel_charge[vehicle]<= 0
            prob += lpSum( # Doesn't go below 0% SOC
                [outputs[period, vehicle] * gv.CHARGER_EFF for period, vehicle in cumul_profile.index]
            ) + cumul_use + rel_charge[vehicle]>= -gv.BATTERY_CAPACITY + charger * gv.TIME_FRACT

    # Max capacity constraint
    n = len(time_periods.unique())
    for period in time_periods:
        time_routes = list(profile_av.loc[period].index)
        prob += lpSum(
            [outputs[period, route] for route in time_routes]) <= capacity[ca]* gv.TIME_FRACT

    # Solve and print to the screen
    prob.solve()
    print(ca, "Partial charge status:", LpStatus[prob.status])
    if prob.status ==-1:
        print('Magic!!')
        df = magic_charging(profile,ca,rel_charge)
    else:
        # Get output variables
        charge_output = []
        for period, route in outputs:
            if prob.status == 1:
                x =  outputs[(period, route)].varValue
            else:
                x = 0
            var_output = {
                'from': period,
                'Vehicle_ID': route,
                output_col: x
            }
            charge_output.append(var_output)

        df = pd.DataFrame.from_records(charge_output).sort_values(['from','Vehicle_ID'])
        df.set_index(['from', 'Vehicle_ID'], inplace=True)
        print('Cost:', value(prob.objective))
    return df

## Create a magic charging schedule to get back to 100% when all else has failed

def magic_charging(profile,ca,rel_charge):
    """Special charging profile

    This chargign doesn't account for site capacity, charger power, state of 
    charge. It simply deliveres the charge required to go back to 100%, at 
    equal power in all available time periods.

    Args:
        profile (DataFrame): empty profile of all vehicles in all time periods
        ca (str): category to use in optimisation (opt, BAU)
        rel_charge (Series): list of intial battery charge state relative to full. 
            Index are Vehicle_ID

    Returns:
        DataFrame: outputs for each vehicle / Time period
    """
    profile_av = profile[profile['Available'] == 1]
    #price_col = gv.CAT_COLS['PRICE'][ca]
    output_col = gv.CAT_COLS['OUTPUT'][ca]
    vehicles = profile.index.get_level_values(1).unique()
    time_periods = profile_av.index.get_level_values(0).unique()
    required_energy = profile['Battery_Use'].groupby('Vehicle_ID').sum() + rel_charge
    num_timeperiods = profile_av['Available'].groupby('Vehicle_ID').count()
    req_output = -required_energy/( gv.CHARGER_EFF* num_timeperiods)
    profile_av[output_col] = 0
    for idx in profile_av.index:
        profile_av.loc[idx,output_col] = req_output.loc[idx[1]]
    return profile_av[[output_col]]