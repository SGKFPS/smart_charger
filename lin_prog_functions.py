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
    """Linear optimisation for a range of dates

    Creates an output for each time period over a range of dates. Runs a linear
    optimisation over each day independently, assuming each day starts with 100% charge.

    Args:
        empty_profile (DataFrame): MultiIndex profile of each vehicle / time period
        charger (int): charger power
        capacity (int): max allowed site capacity

    Returns:
        DataFrame: power outputs for each vehicle / time period
        Array: list of dates in the time period
        String: list of dates when optimisation is unfeasible or there are no journeys
        LpProblem: the last optimisation problem
    """
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
    """Linear optimisation for a single day charging

    This optimiser uses PuLP to find optimal power outputs over a day.
    Objective: reduce overall electricity spend
    Constraint 1: get to 100% final SOC before end of time period of next day departures
    Constraint 2: not go below 0% or over 100% battery charge
    Constraint 3: not go over site capacity

    Args:
        profile (DataFrame): empty profile of a single day
        ca (str): category to use in optimisation (opt, BAU)
        charger (int): charger power
        capacity (int): max allowed site capacity

    Returns:
        DataFrame: Outputs for each time period
        LpProblem: variables, objective and constraints
    """
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
        LpProblem: the last optimisation problem
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
    req_energy = empty_profile.groupby(
        ['date','Vehicle_ID']).sum()[['Battery_Use']]*(
            1+gv.MARGIN_SOC)
    last_day = req_energy.index[-1][0]+dt.timedelta(days=1)
    for v in empty_profile.index.get_level_values('Vehicle_ID').unique():
        req_energy.loc[(last_day,v),'Battery_Use'] = 0
    req_energy['Full_Use'] = -gv.BATTERY_CAPACITY
    req_energy['Req_Battery'] = req_energy[['Battery_Use','Full_Use']].max(axis=1)

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
            next_day = day+dt.timedelta(days=1)
            next_req = req_energy.loc[
                (next_day,slice(None)),'Req_Battery'].droplevel(level=0)
            output_df = {}
            PuLP_prob = {}
            day_profile_out = day_profile.copy()
            for ca in gv.CATS:
                output_df[ca], PuLP_prob[ca], rel_charge[ca], note = linear_optimiser_V4(
                    day_profile,
                    ca,
                    charger[0],charger[1],
                    capacity,
                    rel_charge[ca],
                    next_req
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
                bad_days += note
                for ca in gv.CATS:
                    bad_days += '_'
                    bad_days += str(PuLP_prob[ca].status)
            dates_status += str([date,day_status])
            dates_status += '\n'

    profile_out = pd.concat(all_days_profile)
    return profile_out, dates, bad_days, PuLP_prob

def linear_optimiser_V3(profile,ca,charger,capacity,rel_charge,next_req):
    """Linear optimisation for a single day charging

    This optimiser uses PuLP to find optimal power outputs over a day. 
    Passes incomplete SoC to next day
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
        next_req (Series): battery requirements for next day per vehicle

    Returns:
        DataFrame: Outputs for each time period
        LpProblem: variables, objective and constraints
        Series: end of day final SOC for each vehicle
        str: a note on outcomes of the daily optimisation
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
    note = ''
    # Create the 'prob' variable to contain the problem data
    prob = LpProblem("Multiple_route_scheduling",LpMinimize)

    # Add costs to objective function
    prob += lpSum(
        [profile_av.loc[(period, vehicle), price_col] * outputs[period, vehicle] 
        for period, vehicle in profile_av.index]
        ), "Total Charging costs"

    # Final SOC constraint
    for vehicle in vehicles:
        # Get profile for single vehicle
        vehicle_prof = profile_av.loc[(slice(None),vehicle),'Battery_Use']
        prob += lpSum(
            [outputs[period,vehicle] * gv.CHARGER_EFF for period, vehicle in vehicle_prof.index]
        ) == - (
            profile.loc[(slice(None),vehicle),'Battery_Use'].sum() # Power used that day
            + rel_charge[vehicle] # Initial missing charge
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
        df, note2 = charge_tonextday(profile,ca,charger,capacity,rel_charge,next_req)
        note += '\nMain unfeasible'
        note += note2
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
    return df, prob, final_soc, note

def charge_tonextday(profile,ca,charger1,charger2,capacity,rel_charge,next_req):
    """Optimise charging when 100% is unfeasible
    
    The objective of this function is to charge vehicles to have enough
    for next day's journeys + 10% at the cheapest price and deliver as much charge as possible

    Args:
        profile (DataFrame): empty profile of a single day
        ca (str): category to use in optimisation (opt, BAU)
        charger1 (int): slow charger power
        charger2 (int): fast charger power
        capacity (int): max allowed site capacity
        rel_charge (Series): list of intial battery charge state relative to full. 
            Index are Vehicle_ID
        next_req (Series): battery requirements for next day per vehicle

    Returns:
        DataFrame: outputs per time period
    """
    profile_av = profile[profile['Available'] == 1]
    price_col = gv.CAT_COLS['PRICE'][ca]
    output_col = gv.CAT_COLS['OUTPUT'][ca]
    ch_col = gv.CAT_COLS['CH_TYPE'][ca]
    vehicles = profile.index.get_level_values(1).unique()
    time_periods = profile_av.index.get_level_values(0).unique()
    sessions = profile['Session'].unique()
    # Define output variable
    outputs = LpVariable.dicts(
        "output",
        ((period, vehicle) for period, vehicle in profile_av.index),
        lowBound = 0,
        upBound = charger2 * gv.TIME_FRACT,
        cat = "Continuous"
        )
    # Define choice of charger variable
    ch_assignment = LpVariable.dicts(
        "Charger",
        (session for session in sessions),
        cat = 'Binary'
    )
    note=''
    # Create the 'prob' variable to contain the problem data
    prob = LpProblem("Charge to next day reqs",LpMinimize)

    # Add costs to objective function
    prob += lpSum(
        [(profile_av.loc[(period, vehicle), price_col] -100 )* outputs[period, vehicle] 
        for period, vehicle in profile_av.index]
        ), "Total Charging costs + Total Outputs"

    # Charge power constraint
    for period, vehicle in profile_av.index:
        prob += outputs[period, vehicle] <= ((charger1 
        + ch_assignment[profile_av.loc[(period,vehicle),'Session']] * (charger2-charger1))
            * gv.TIME_FRACT)

    # Final SOC constraint
    for vehicle in vehicles:
        # Get profile for single vehicle
        vehicle_prof = profile_av.loc[(slice(None),vehicle),'Battery_Use']
        prob += lpSum(
            [outputs[period,vehicle] * gv.CHARGER_EFF for period, vehicle in vehicle_prof.index]
        ) >= - (
            profile.loc[(slice(None),vehicle),'Battery_Use'].sum()# Power used that day
            + rel_charge[vehicle]# Initial missing charge
            + gv.BATTERY_CAPACITY # Back to 0% charge
            + next_req.loc[vehicle]
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
            ) + cumul_use + rel_charge[vehicle] >= (
                -gv.BATTERY_CAPACITY + gv.TIME_FRACT * (charger1
                + ch_assignment[profile_av.loc[(period,vehicle),'Session']] 
                * (charger2-charger1)))

    # Max capacity constraint
    n = len(time_periods.unique())
    for period in time_periods:
        time_veh = list(profile_av.loc[period].index) # Selects the vehicles available at time
        prob += lpSum(
            [outputs[period, vehicle] for vehicle in time_veh]) <= capacity[ca]* gv.TIME_FRACT
        prob += lpSum(
            [ch_assignment[profile_av.loc[(period,vehicle),'Session']] for vehicle in time_veh]
            ) <= gv.NUM_FAST_CH

    # Solve and print to the screen
    prob.solve()
    print(ca, "Next required charge status:", LpStatus[prob.status])
    if prob.status ==-1:
        print('Magic!!')
        note += '\nMagic!' # TODO change this to go first to breach scenario
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
    return df, note

def charge_tonextday_breach(profile,ca,charger1,charger2,capacity,rel_charge,next_req):
    """Optimise charging breaching site capacity
    
    The objective of this function is to charge vehicles to have enough
    for next day's journeys + 10% at the cheapest price and deliver as much charge as possible.
    This method allows breaching site capacity (up to a limit)

    Args:
        profile (DataFrame): empty profile of a single day
        ca (str): category to use in optimisation (opt, BAU)
        charger1 (int): slow charger power
        charger2 (int): fast charger power
        capacity (int): max allowed site capacity
        rel_charge (Series): list of intial battery charge state relative to full. 
            Index are Vehicle_ID
        next_req (Series): battery requirements for next day per vehicle

    Returns:
        DataFrame: outputs per time period
    """
    profile_av = profile[profile['Available'] == 1]
    price_col = gv.CAT_COLS['PRICE'][ca]
    output_col = gv.CAT_COLS['OUTPUT'][ca]
    ch_col = gv.CAT_COLS['CH_TYPE'][ca]
    vehicles = profile.index.get_level_values(1).unique()
    time_periods = profile_av.index.get_level_values(0).unique()
    sessions = profile['Session'].unique()
    # Define output variable
    outputs = LpVariable.dicts(
        "output",
        ((period, vehicle) for period, vehicle in profile_av.index),
        lowBound = 0,
        upBound = charger2 * gv.TIME_FRACT,
        cat = "Continuous"
        )
    # Define choice of charger variable
    ch_assignment = LpVariable.dicts(
        "Charger",
        (session for session in sessions),
        cat = 'Binary'
    )
    # Select time periods that breach site capacity
    time_breaches = LpVariable.dicts(
        "Breach",
        (time for time in time_periods),
        cat = 'Binary'
    )
    note=''
    # Create the 'prob' variable to contain the problem data
    prob = LpProblem("Charge to next day reqs, breach cap",LpMinimize)

    # Add costs to objective function
    prob += lpSum(
        [(profile_av.loc[(period, vehicle), price_col] -100 )* outputs[period, vehicle] 
        for period, vehicle in profile_av.index]
        ), "Total Charging costs + Total Outputs"

    # Charge power constraint
    for period, vehicle in profile_av.index:
        prob += outputs[period, vehicle] <= ((charger1 
        + ch_assignment[profile_av.loc[(period,vehicle),'Session']] * (charger2-charger1))
            * gv.TIME_FRACT)

    # Final SOC constraint
    for vehicle in vehicles:
        # Get profile for single vehicle
        vehicle_prof = profile_av.loc[(slice(None),vehicle),'Battery_Use']
        prob += lpSum(
            [outputs[period,vehicle] * gv.CHARGER_EFF for period, vehicle in vehicle_prof.index]
        ) >= - (
            profile.loc[(slice(None),vehicle),'Battery_Use'].sum()# Power used that day
            + rel_charge[vehicle]# Initial missing charge
            + gv.BATTERY_CAPACITY # Back to 0% charge
            + next_req.loc[vehicle]
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
            ) + cumul_use + rel_charge[vehicle] >= (
                -gv.BATTERY_CAPACITY + gv.TIME_FRACT * (charger1
                + ch_assignment[profile_av.loc[(period,vehicle),'Session']] 
                * (charger2-charger1)))

    # Max capacity constraint
    #TODO change here
    n = len(time_periods.unique())
    for period in time_periods:
        time_veh = list(profile_av.loc[period].index) # Selects the vehicles available at time
        prob += lpSum(
            [outputs[period, vehicle] for vehicle in time_veh]) <= capacity[ca]* gv.TIME_FRACT
        prob += lpSum(
            [ch_assignment[profile_av.loc[(period,vehicle),'Session']] for vehicle in time_veh]
            ) <= gv.NUM_FAST_CH

    # Solve and print to the screen
    prob.solve()
    print(ca, "Next required charge status:", LpStatus[prob.status])
    if prob.status ==-1:
        print('Magic!!')
        note += '\nMagic!'
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
    return df, note

# Incomplete charging when 100% unfeasible
def charge_incomplete(profile,ca,charger1,charger2,capacity,rel_charge):
    """Optimise charging when 100% is unfeasible
    
    The objective of this function is to deliver as much charge as possible
    without accounting for required final SOC. If this is unfeasible, it will go 
    to magic charging.

    Args:
        profile (DataFrame): empty profile of a single day
        ca (str): category to use in optimisation (opt, BAU)
        charger1 (int): slow charger power
        charger2 (int): fast charger power
        capacity (int): max allowed site capacity
        rel_charge (Series): list of intial battery charge state relative to full. 
            Index are Vehicle_ID

    Returns:
        DataFrame: outputs per time period
    """
    profile_av = profile[profile['Available'] == 1]
    price_col = gv.CAT_COLS['PRICE'][ca]
    output_col = gv.CAT_COLS['OUTPUT'][ca]
    ch_col = gv.CAT_COLS['CH_TYPE'][ca]
    vehicles = profile.index.get_level_values(1).unique()
    time_periods = profile_av.index.get_level_values(0).unique()
    sessions = profile['Session'].unique()
    # Define output variable
    outputs = LpVariable.dicts(
        "output",
        ((period, vehicle) for period, vehicle in profile_av.index),
        lowBound = 0,
        upBound = charger2 * gv.TIME_FRACT,
        cat = "Continuous"
        )
    ch_assignment = LpVariable.dicts(
        "Charger",
        (session for session in sessions),
        cat = 'Binary'
    )

    # Create the 'prob' variable to contain the problem data
    prob = LpProblem("Multiple_route_scheduling",LpMaximize)

    # Add costs to objective function
    prob += lpSum(
        [outputs[period, vehicle] for period, vehicle in profile_av.index]
        ), "Total Charging"

    # Charge power constraint
    for period, vehicle in profile_av.index:
        prob += outputs[period, vehicle] <= ((charger1 
        + ch_assignment[profile_av.loc[(period,vehicle),'Session']] * (charger2-charger1))
            * gv.TIME_FRACT)

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
            ) + cumul_use + rel_charge[vehicle] >= (
                -gv.BATTERY_CAPACITY + gv.TIME_FRACT * (charger1
                + ch_assignment[profile_av.loc[(period,vehicle),'Session']] 
                * (charger2-charger1)))

    # Max capacity constraint
    n = len(time_periods.unique())
    for period in time_periods:
        time_veh = list(profile_av.loc[period].index) # Selects the vehicles available at time
        prob += lpSum(
            [outputs[period, vehicle] for vehicle in time_veh]) <= capacity[ca]* gv.TIME_FRACT
        prob += lpSum(
            [ch_assignment[profile_av.loc[(period,vehicle),'Session']] for vehicle in time_veh]
            ) <= gv.NUM_FAST_CH

    # Solve and print to the screen
    prob.solve()
    print(ca, "Partial charge status:", LpStatus[prob.status])
    if prob.status ==-1:
        print('Magic!!')
        df = magic_charging(profile,ca,rel_charge)
    else:
        # Get output variables
        charge_output = []
        for period, vehicle in outputs:
            if prob.status == 1:
                x =  outputs[(period, vehicle)].varValue
                y = ch_assignment[profile_av.loc[(period,vehicle),'Session']].varValue
            else:
                x = 0
            var_output = {
                'from': period,
                'Vehicle_ID': vehicle,
                output_col: x,
                ch_col: y
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

def linear_optimiser_V4(profile,ca,charger1,charger2,capacity,rel_charge,next_req):
    """Linear optimisation for a single day charging

    This optimiser uses PuLP to find optimal power outputs over a day.
    Uses 2 different charger powers
    Objective: reduce overall electricity spend
    Constraint 1: get to 100% final SOC before end of time period of next day departures
    Constraint 2: not go below 0% or over 100% battery charge
    Constraint 3: not go over site capacity
    If this is unfeasible, it will atempt to charge as much as possible using
    incomplete_charge.

    Args:
        profile (DataFrame): empty profile of a single day
        ca (str): category to use in optimisation (opt, BAU)
        charger1 (int): slow charger power
        charger2 (int): fast charger power
        capacity (int): max allowed site capacity
        rel_charge (Series): list of intial battery charge state relative to full. 
            Index are Vehicle_ID
        next_req (Series): battery requirements for next day per vehicle

    Returns:
        DataFrame: Outputs for each time period
        LpProblem: variables, objective and constraints
        Series: end of day final SOC for each vehicle
        str: a note on outcomes of the daily optimisation
    """
    profile_av = profile[profile['Available'] == 1]
    price_col = gv.CAT_COLS['PRICE'][ca]
    output_col = gv.CAT_COLS['OUTPUT'][ca]
    ch_col = gv.CAT_COLS['CH_TYPE'][ca]
    vehicles = profile.index.get_level_values(1).unique()
    time_periods = profile_av.index.get_level_values(0).unique()
    sessions = profile['Session'].unique()
    
    # Define output variable
    outputs = LpVariable.dicts(
        "output",
        ((period, vehicle) for period, vehicle in profile_av.index),
        lowBound = 0,
        upBound = charger2 * gv.TIME_FRACT,
        cat = "Continuous"
        )
    ch_assignment = LpVariable.dicts(
        "Charger",
        (session for session in sessions),
        cat = 'Binary'
    )
    note = ''
    # Create the 'prob' variable to contain the problem data
    prob = LpProblem("Multiple_route_scheduling",LpMinimize)

    # Add costs to objective function
    prob += lpSum(
        [profile_av.loc[(period, vehicle), price_col] * outputs[period, vehicle] 
        for period, vehicle in profile_av.index]
        ), "Total Charging costs"

    # Charge power constraint
    for period, vehicle in profile_av.index:
        prob += outputs[period, vehicle] <= ((charger1 
        + ch_assignment[profile_av.loc[(period,vehicle),'Session']] * (charger2-charger1))
            * gv.TIME_FRACT)

    # Final SOC constraint
    for vehicle in vehicles:
        # Get profile for single vehicle
        vehicle_prof = profile_av.loc[(slice(None),vehicle),'Battery_Use']
        prob += lpSum(
            [outputs[period,vehicle] * gv.CHARGER_EFF for period, vehicle in vehicle_prof.index]
        ) == - (
            profile.loc[(slice(None),vehicle),'Battery_Use'].sum() # Power used that day
            + rel_charge[vehicle] # Initial missing charge
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
            ) + cumul_use + rel_charge[vehicle] >= (
                -gv.BATTERY_CAPACITY + gv.TIME_FRACT * (charger1
                + ch_assignment[profile_av.loc[(period,vehicle),'Session']] 
                * (charger2-charger1)))

    # Max capacity constraint
    n = len(time_periods.unique())
    for period in time_periods:
        time_veh = list(profile_av.loc[period].index) # Selects the vehicles available at time
        prob += lpSum(
            [outputs[period, vehicle] for vehicle in time_veh]) <= capacity[ca]* gv.TIME_FRACT
        prob += lpSum(
            [ch_assignment[profile_av.loc[(period,vehicle),'Session']] for vehicle in time_veh]
            ) <= gv.NUM_FAST_CH

    # Solve and print to the screen
    prob.solve()
    print(ca, "status:", LpStatus[prob.status])
    # If unfeasible, tries to 
    if  prob.status == -1:
        df, note2 = charge_tonextday(profile,ca,charger1,charger2,capacity,rel_charge,next_req)
        note += '\nMain unfeasible'
        note += note2
    else:
        # Get output variables
        charge_output = []
        for period, vehicle in outputs:
            if prob.status == 1:
                x =  outputs[(period, vehicle)].varValue
                y = ch_assignment[profile_av.loc[(period,vehicle),'Session']].varValue
            else:
                x = 0
            var_output = {
                'from': period,
                'Vehicle_ID': vehicle,
                output_col: x,
                ch_col: y
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
    return df, prob, final_soc, note