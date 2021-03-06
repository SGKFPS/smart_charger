# Stores all prototypoe linear_optimiser functions

import numpy as np
import global_variables as gv
import testdata_proc as pf
import pandas as pd
import datetime as dt
from pulp import *
import time
import cvxpy as cp
from cvxopt.modeling import variable, op, max, sum

def optimise_range(empty_profile, charger, capacity,
                    dictV, batteries):
    """Linear optimisation for a range of dates with a mixed fleet

    Creates an output for each time period over a range of dates. Runs
    a linear optimisation over each day independently, passing the
    final SOC to the next day.

    Args:
        empty_profile (DataFrame): MultiIndex profile of each vehicle
                                    / time period
        charger (list): list of charger powers
        capacity (dict): dict. of max allowed site capacity per category
        dictV (dict): dictionary of vehicle IDs and model

    Returns:
        DataFrame: power outputs for each vehicle / time period
        Array: list of dates in the time period
        String: list of dates when optimisation is unfeasible or there
                are no journeys
        LpProblem: the last optimisation problem
    """
    dates = np.unique(empty_profile[0].date)
    vehiclelist = [int(v['Vehicle_ID'].unique()[0]) for v in empty_profile]
    print(dates)
    print(vehiclelist)


    nVeh = len(vehiclelist)
    battery_cap = {k: gv.VSPEC[dictV[k]]['C'] for k in dictV.keys()}
    all_days_profile = []
    dates_status = pd.DataFrame(columns=gv.CATS)
    bad_days = '\nBad days:\n'
    # status = 0
    initial_rel_charge = pd.Series(
        data=[0]*nVeh,
        index=vehiclelist
    )
    # print(initial_rel_charge)
    rel_charge = dict.fromkeys(gv.CATS, initial_rel_charge)
    req_energy = [e.groupby('date').sum()[['Battery_Use']]*(1+gv.MARGIN_SOC) for e in empty_profile]
    # print(req_energy)
    last_day = pd.Timestamp(dates[-1]).to_pydatetime()+dt.timedelta(days=1)

    for req, v in zip(req_energy, vehiclelist):
        req.loc[last_day, 'Battery_Use'] = 0
        req['Full_Use'] = -1 * battery_cap[v]
        req['Req_Battery'] = req[['Battery_Use', 'Full_Use']].max(axis=1)
    # print(req_energy)

    level_optimiser = []
    bat_out = []
    for date in dates:
        day_status = ""
        start = time.process_time()
        #print(date)
        day = dt.datetime.combine(pd.Timestamp(date).to_pydatetime(), dt.datetime.min.time())
        day_profile = pf.create_daily(empty_profile, day)
        days = pf.create_dailys(empty_profile, day)
        #print(day_profile)
        if len(day_profile) == 0:
            bad_days += '\nEmpty day:'
            bad_days += str(date)
            dates_status.loc[day] = 'Empty'
            pass
        else:
            #print(req_energy)
            next_day = day+dt.timedelta(days=1)
            next_req = [r.loc[next_day, 'Req_Battery'] for r in req_energy]
            #print(next_req)
            output_df = {}
            PuLP_prob = {}
            bat_df = {}
            day_profile_out = days.copy()
            day_level = []
            for ca in gv.CATS:
                # print(charger[0])
                # print(charger[-1])
                (output_df[ca], PuLP_prob[ca], rel_charge[ca], note,
                    dates_status.loc[day, ca], bat_df[ca]) = linear_optimiser_V7(
                    day_profile, ca,
                    charger[0], charger[-1],
                    capacity[ca], rel_charge[ca], next_req,
                    battery_cap)
                day_profile_out = day_profile_out.merge(
                    output_df[ca],
                    how='left',
                    left_index=True,
                    right_index=True,
                    )
                bat_out.append(bat_df[ca])
                day_profile_out.fillna(0, inplace=True)
                day_status += PuLP_prob[ca].status
            # print(
            #     date,
            #     # '\nTime:', time.process_time() - start,
            #     'Status:', day_status,
            #     ':', PuLP_prob[gv.CATS[0]].status)
            all_days_profile.append(day_profile_out)
            #print(len(gv.CATS))
            if day_status != 'optimal':
                bad_days += '\nNon-Optimal: '
                bad_days += str(date)
                bad_days += note
                for ca in gv.CATS:
                    bad_days += '_'
                    bad_days += str(PuLP_prob[ca].status)
    profile_out = pd.concat(all_days_profile)
    dates_status.rename(columns=gv.CAT_COLS['LEVEL'], inplace=True)
    return profile_out, dates, bad_days, PuLP_prob, dates_status, bat_out

def linear_optimiser_V7(profile, ca, charger1, charger2,
                        capacity, rel_charge, next_req, battery_cap):
    """Linear optimisation for a single day charging, mixed fleet

    This optimiser uses PuLP to find optimal power outputs over a day.
    Uses 2 different charger powers, and a varying site capacity.
    Objective: reduce overall electricity spend
    Constraint 1: get to 100% final SOC before end of time period
        of next day departures
    Constraint 2: not go below 0% or over 100% battery charge
    Constraint 3: not go over site capacity
    If this is unfeasible, it will atempt to charge as much as possible
    using incomplete_charge.

    Args:
        profile (DataFrame): empty profile of a single day
        ca (str): category to use in optimisation (opt, BAU)
        charger1 (int): slow charger power
        charger2 (int): fast charger power
        capacity (Series): max allowed site capacity per time period
        rel_charge (Series): list of intial battery charge state
            relative to full. Index are Vehicle_ID
        next_req (Series): battery requirements for next day per vehicle
        battery_cap (dict): dictionary of vehicle ID and their capacity

    Returns:
        DataFrame: Outputs for each time period
        LpProblem: variables, objective and constraints
        Series: end of day final SOC for each vehicle
        str: a note on outcomes of the daily optimisation
        opt_level (str): the level of optimisation that was feasible
    """
    #print(profile[0]['Vehicle_ID'])
    vehicles = [int(p['Vehicle_ID'].unique()) for p in profile]
    
    profile_av = [p[p['Available'] == 1] for p in profile]
    time_periods = profile[0]['from']
    price_col = gv.CAT_COLS['PRICE'][ca]
    prices = profile[0][price_col].values
    
    #print(price_col)
    output_col = gv.CAT_COLS['OUTPUT'][ca]
    ch_col = gv.CAT_COLS['CH_TYPE'][ca]
    
    #print([v['Return'] for v in profile])
    
    sessions = [list(p['Session'].unique()) for p in profile]
    sessions = [x for sublist in sessions for x in sublist]
    sessions = list(np.unique(np.array(sessions)))
    print(sessions)
    
    # Define output variable

    outputs = cp.Variable((len(time_periods), len(vehicles)), nonneg=True)
    ch_assignment = cp.Variable(len(sessions), boolean=True)
    battery = cp.Variable(len(time_periods))

    constraints = []

    constraints.append(outputs <= charger2 * gv.TIME_FRACT)
    constraints.append(battery >= -1 * charger2 * gv.TIME_FRACT)
    constraints.append(battery <= charger2 * gv.TIME_FRACT)
    constraints.append(battery == 0)
    constraints.append(cp.sum(battery) >= 0)
    constraints.append(cp.sum(battery) <= 100)

    #print(True in constraints)

    # battery charge/discharge constraints
    for i in range(len(time_periods)):
        constraints.append(-battery[i] <= cp.sum(outputs[i, :]))

    #print(True in constraints)
    for vehicle in range(len(vehicles)):
        times = list(profile[vehicle].loc[profile[vehicle]['Available'] == 1].index)
        for t in times:
            constraints.append( outputs[t, vehicle] <= ((
                charger1 + ch_assignment[
                    sessions.index(profile[vehicle].loc[t, 'Session'])]
                * (charger2-charger1)) * gv.TIME_FRACT))

    #print(True in constraints)
    for vehicle in range(len(vehicles)):
        times = list(profile[vehicle].loc[profile[vehicle]['Available'] == 1].index)
        #print(times)
        constraints.append(cp.sum([outputs[i, vehicle] * gv.CHARGER_EFF for i in times])
                            == -1* ( profile[vehicle]['Battery_Use'].sum() + rel_charge[vehicles[vehicle]]))

    #print(True in constraints)
    #print(vehicles)
    for vehicle in range(len(vehicles)):
        #vehicle_prof = profile_av.loc[(slice(None), vehicle), 'Battery_Use']
        for period in range(len(time_periods)):
            cumul_use = profile[vehicle].loc[:period,'Battery_Use'].sum() # cummulative up to that point
            temp = profile[vehicle].iloc[:period]
            cumul_profile = list(temp.loc[temp['Available'] == 1].index) # up to that point
            constraints.append(cp.sum(  # Doesn't go over 100% SOC
                [outputs[i, vehicle] * gv.CHARGER_EFF
                    for i in cumul_profile]
            ) + cumul_use + rel_charge[vehicles[vehicle]] <= cp.Constant(0.00001))
        # Make sure it doesn't go below 0% SOC at every return
        returns = list(profile[vehicle].loc[profile[vehicle]['Return'] == 1].index)
        #print(profile[vehicle].loc[returns])
        for period in returns:
            cumul_use = profile[vehicle].loc[:period,'Battery_Use'].sum() # cummulative up to that point
            temp = profile[vehicle].iloc[:period]
            cumul_profile = list(temp.loc[temp['Available'] == 1].index) # up to that point
            constraints.append(cp.sum(  # Doesn't go below 0% SOC
                [outputs[i, vehicle] * gv.CHARGER_EFF for i in cumul_profile]
            ) + cumul_use + rel_charge[vehicles[vehicle]] + battery_cap[vehicles[vehicle]] >= cp.Constant(0))
    
    #print(True in constraints)

    for idx, time in enumerate(time_periods):
        constraints.append( cp.sum(  # limits the overall site capacity
            outputs[idx, :] + battery[idx]) <= (
                capacity.loc[time] * gv.TIME_FRACT))
        constraints.append( cp.sum(  # limits the number of fast chargers
            [ch_assignment[
                sessions.index(profile[v-1].loc[idx, 'Session'])] for v in vehicles ]) <= gv.NUM_FAST_CH)
    
    note = ''

    all_prices = [np.array(prices) for _ in range(len(vehicles))]
    all_prices = np.stack(all_prices, axis=1)
    #print(np.zeros((len(time_periods), len(vehicles))))
    #all_prices = all_prices.reshape((len(time_periods), len(vehicles)))
    #print(all_prices)
    #print(outputs)


    objective = cp.Minimize(cp.sum(cp.multiply(outputs, all_prices)))
    
    problem = cp.Problem(objective, constraints)

    # Solve and print to the screen
    problem.solve(solver=cp.CBC)

    #print(problem.status)
    #print(ca, "status:", LpStatus[prob.status])
    # If unfeasible, tries to charge to next day
    if problem.status in ["infeasible", "unbounded"]:
        print("=========================================")
        # df = magic_charging(profile, ca, rel_charge)
        df, note2, opt_level = charge_tonextday(
            profile, ca, charger1, charger2, capacity,
            rel_charge, next_req, battery_cap)
        note += '\nMain unfeasible'
        note += note2
    else:
        # Get output variables
        charge_output = []
        for vehicle in vehicles:
            for period in range(len(time_periods)):
                if problem.status == 'optimal':
                    x = outputs.value[period, vehicle-1]
                    y = ch_assignment.value[
                        sessions.index(profile[vehicle-1].loc[period, 'Session'])]
                else:
                    x = 0
                var_output = {
                    'from': time_periods[period],
                    'Vehicle_ID': vehicle,
                    output_col: x,
                    ch_col: y
                }
                charge_output.append(var_output)
        bat_output = []
        for bat, time in zip(battery, range(len(time_periods))):
            if problem.status == 'optimal':
                x = battery.value[time]
            else:
                x = 0
            var_output = {
                'from': time_periods[time],
                'Battery_ID': 0,
                output_col: x,
            }
            bat_output.append(var_output)
        
        opt_level = 'Main'
        df = pd.DataFrame.from_records(charge_output).sort_values(
            ['from', 'Vehicle_ID'])
        df.set_index(['from', 'Vehicle_ID'], inplace=True)
        dfb = pd.DataFrame.from_records(bat_output).sort_values(
            ['from', 'Battery_ID']
        )
        
    # Generate a final SoC array
    #print([profile[i-1]['Battery_Use'].sum() for i in vehicles])
    final_soc = (rel_charge + (
        df.groupby('Vehicle_ID').sum()[output_col]*gv.CHARGER_EFF
        + [profile[i-1]['Battery_Use'].sum() for i in vehicles])).round(6)
    #print(final_soc)
    return df, problem, final_soc, note, opt_level, dfb


def optimise_range3(empty_profile, charger, capacity,
                    dictV, batteries):
    """Linear optimisation for a range of dates with a mixed fleet

    Creates an output for each time period over a range of dates. Runs
    a linear optimisation over each day independently, passing the
    final SOC to the next day.

    Args:
        empty_profile (DataFrame): MultiIndex profile of each vehicle
                                    / time period
        charger (list): list of charger powers
        capacity (dict): dict. of max allowed site capacity per category
        dictV (dict): dictionary of vehicle IDs and model

    Returns:
        DataFrame: power outputs for each vehicle / time period
        Array: list of dates in the time period
        String: list of dates when optimisation is unfeasible or there
                are no journeys
        LpProblem: the last optimisation problem
    """
    dates = np.unique(empty_profile.index.get_level_values(0).date)
    vehiclelist = empty_profile.index.get_level_values(
        'Vehicle_ID').unique()
    nVeh = len(vehiclelist)
    battery_cap = {k: gv.VSPEC[dictV[k]]['C'] for k in dictV.keys()}
    all_days_profile = []
    dates_status = pd.DataFrame(columns=gv.CATS)
    bad_days = '\nBad days:\n'
    # status = 0
    initial_rel_charge = pd.Series(
        data=[0]*nVeh,
        index=empty_profile.index.get_level_values(1).unique()
    )
    rel_charge = dict.fromkeys(gv.CATS, initial_rel_charge)
    req_energy = empty_profile.groupby(
        ['date', 'Vehicle_ID']).sum()[['Battery_Use']]*(
            1+gv.MARGIN_SOC)
    print(req_energy)
    last_day = req_energy.index[-1][0]+dt.timedelta(days=1)
    for v in vehiclelist:
        req_energy.loc[(last_day, v), 'Battery_Use'] = 0
    req_energy['Full_Use'] = -req_energy.index.get_level_values(
        'Vehicle_ID').map(battery_cap)
    req_energy['Req_Battery'] = req_energy[[
        'Battery_Use', 'Full_Use']].max(
        axis=1)
    print(req_energy)
    level_optimiser = []
    bat_out = []
    for date in dates:
        day_status = 0
        start = time.process_time()
        day = dt.datetime.combine(date, dt.datetime.min.time())
        day_profile = pf.create_daily_schedule(empty_profile, day)
        if len(day_profile) == 0:
            bad_days += '\nEmpty day:'
            bad_days += str(date)
            dates_status.loc[day] = 'Empty'
            pass
        else:
            next_day = day+dt.timedelta(days=1)
            next_req = req_energy.loc[
                (next_day, slice(None)), 'Req_Battery'].droplevel(level=0)
            output_df = {}
            PuLP_prob = {}
            bat_df = {}
            day_profile_out = day_profile.copy()
            day_level = []
            for ca in gv.CATS:
                # print(charger[0])
                # print(charger[-1])
                (output_df[ca], PuLP_prob[ca], rel_charge[ca], note,
                    dates_status.loc[day, ca], bat_df[ca]) = linear_optimiser_V6(
                    day_profile, ca,
                    charger[0], charger[-1],
                    capacity[ca], rel_charge[ca], next_req,
                    battery_cap)
                day_profile_out = day_profile_out.merge(
                    output_df[ca],
                    how='left',
                    left_index=True,
                    right_index=True,
                    )
                bat_out.append(bat_df[ca])
                day_profile_out.fillna(0, inplace=True)
                day_status += PuLP_prob[ca].status
            # print(
            #     date,
            #     # '\nTime:', time.process_time() - start,
            #     'Status:', day_status,
            #     ':', PuLP_prob[gv.CATS[0]].status)
            all_days_profile.append(day_profile_out)
            if day_status < len(gv.CATS):
                bad_days += '\nNon-Optimal: '
                bad_days += str(date)
                bad_days += note
                for ca in gv.CATS:
                    bad_days += '_'
                    bad_days += str(PuLP_prob[ca].status)
    profile_out = pd.concat(all_days_profile)
    dates_status.rename(columns=gv.CAT_COLS['LEVEL'], inplace=True)
    return profile_out, dates, bad_days, PuLP_prob, dates_status, bat_out


def charge_tonextday(profile, ca, charger1, charger2,
                     capacity, rel_charge, next_req, battery_cap):
    """Optimise charging when 100% is unfeasible

    The objective of this function is to charge vehicles to have enough
    for next day's journeys + 10% at the cheapest price and deliver as
    much charge as possible

    Args:
        profile (DataFrame): empty profile of a single day
        ca (str): category to use in optimisation (opt, BAU)
        charger1 (int): slow charger power
        charger2 (int): fast charger power
        capacity (int): max allowed site capacity
        rel_charge (Series): list of intial battery charge state
            relative to full. Index are Vehicle_ID
        next_req (Series): battery requirements for next day per vehicle
        battery_cap (dict): dictionary of vehicle ID and their capacity

    Returns:
        DataFrame: outputs per time period
        opt_level (str)
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
        lowBound=0,
        upBound=charger2 * gv.TIME_FRACT,
        cat="Continuous"
        )
    # Define choice of charger variable
    ch_assignment = LpVariable.dicts(
        "Charger",
        (session for session in sessions),
        cat='Binary'
    )
    note = ''
    # Create the 'prob' variable to contain the problem data
    prob = LpProblem("Charge to next day reqs", LpMinimize)

    # Add costs to objective function
    prob += lpSum(
        [(profile_av.loc[(period, vehicle), price_col] - 100)
            * outputs[period, vehicle] for period, vehicle in profile_av.index]
        ), "Total Charging costs + Total Outputs"

    # Charge power constraint
    for period, vehicle in profile_av.index:
        prob += (outputs[period, vehicle]
                 <= ((charger1
                      + ch_assignment[profile_av.loc[
                          (period, vehicle), 'Session']]
                      * (charger2-charger1))
                     * gv.TIME_FRACT))

    # Final SOC constraint
    for vehicle in vehicles:
        # Get profile for single vehicle
        vehicle_prof = profile_av.loc[(slice(None), vehicle), 'Battery_Use']
        prob += lpSum(
            [outputs[period, vehicle] * gv.CHARGER_EFF
                for period, vehicle in vehicle_prof.index]
        ) >= - (
            profile.loc[(slice(None), vehicle), 'Battery_Use'].sum()
            + rel_charge[vehicle]  # Initial missing charge
            + battery_cap[vehicle]  # Back to 0% charge
            + next_req.loc[vehicle]
        )
    #print('well!')
    # Intermediate SOC constraints
    for vehicle in vehicles:
        vehicle_prof = profile_av.loc[(slice(None), vehicle), 'Battery_Use']
        for period in vehicle_prof.index.get_level_values(0):
            cumul_use = profile.loc[(slice(period), vehicle),
                                    'Battery_Use'].sum()
            cumul_profile = profile_av.loc[(slice(period), vehicle),
                                           'Battery_Use']
            prob += lpSum(  # Doesn't go over 100% SOC
                [outputs[period, vehicle] * gv.CHARGER_EFF
                    for period, vehicle in cumul_profile.index]
            ) + cumul_use + rel_charge[vehicle] <= 0.00001
        # Make sure it doesn't go below 0% SOC at every return
        profile_ret = profile[profile['Return'] == 1]
        #print('heh')
        
        if vehicle in profile_ret.index.get_level_values('Vehicle_ID'):
            returns = profile_ret.loc[(slice(None), vehicle), 'Battery_Use']
            for period in returns.index.get_level_values(0):
                cumul_use = profile.loc[(slice(period), vehicle),
                                        'Battery_Use'].sum()
                cumul_profile = profile_av.loc[
                    (slice(period), vehicle), 'Battery_Use']
                prob += lpSum(  # Doesn't go below 0% SOC
                    [outputs[period, v] * gv.CHARGER_EFF
                        for period, v in cumul_profile.index]
                ) + cumul_use + rel_charge[vehicle] + battery_cap[vehicle] >= 0

    # Max capacity constraint
    n = len(time_periods.unique())
    for period in time_periods:
        #  vehicles available at time
        time_veh = list(profile_av.loc[period].index)
        prob += (lpSum(
            [outputs[period, vehicle] for vehicle in time_veh])
            <= capacity.loc[period] * gv.TIME_FRACT)
        prob += lpSum(
            [ch_assignment[profile_av.loc[(period, v), 'Session']]
                for v in time_veh]) <= gv.NUM_FAST_CH

    # Solve and print to the screen
    prob.solve()
    print(ca, "Next required charge status:", LpStatus[prob.status])
    if prob.status == -1:
        print('Breach!')
        note += '\nBreach!'
        df, note2, opt_level = charge_tonextday_breach(
            profile, ca, charger1, charger2,
            capacity, rel_charge, next_req, battery_cap)
        note += note2
    else:
        # Get output variables
        charge_output = []
        for period, vehicle in outputs:
            if prob.status == 1:
                x = outputs[(period, vehicle)].varValue
                y = ch_assignment[
                    profile_av.loc[(period, vehicle), 'Session']].varValue
            else:
                x = 0
                y = 0
            var_output = {
                'from': period,
                'Vehicle_ID': vehicle,
                output_col: x,
                ch_col: y
            }
            opt_level = 'Tonext'
            charge_output.append(var_output)
        df = pd.DataFrame.from_records(
            charge_output).sort_values(['from', 'Vehicle_ID'])
        df.set_index(['from', 'Vehicle_ID'], inplace=True)
        print('Cost:', value(prob.objective))
    return df, note, opt_level


def charge_tonextday_breach(profile, ca, charger1, charger2,
                            capacity, rel_charge, next_req,
                            battery_cap):
    """Optimise charging breaching site capacity

    The objective of this function is to charge vehicles to have enough
    for next day's journeys + 10% at the cheapest price and deliver as
    much charge as possible.
    This method allows breaching site capacity (up to a limit)

    Args:
        profile (DataFrame): empty profile of a single day
        ca (str): category to use in optimisation (opt, BAU)
        charger1 (int): slow charger power
        charger2 (int): fast charger power
        capacity (int): max allowed site capacity
        rel_charge (Series): list of intial battery charge state
            relative to full. Index are Vehicle_ID
        next_req (Series): battery requirements for next day per vehicle
        battery_cap (dict): dictionary of vehicle ID and their capacity

    Returns:
        DataFrame: outputs per time period
        str: note about the optimisation
        opt_level (str)
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
        lowBound=0,
        upBound=charger2 * gv.TIME_FRACT,
        cat="Continuous")
    # Define choice of charger variable
    ch_assignment = LpVariable.dicts(
        "Charger",
        (session for session in sessions),
        cat='Binary')
    # Select time periods that breach site capacity
    time_breaches = LpVariable.dicts(
        "Breach",
        (time for time in time_periods),
        cat='Binary')
    note = ''
    # Create the 'prob' variable to contain the problem data
    prob = LpProblem("Charge to next day reqs, breach cap", LpMinimize)

    # Add costs to objective function
    prob += lpSum(
        [(profile_av.loc[(period, vehicle), price_col] - 100)
         * outputs[period, vehicle]
            for period, vehicle in profile_av.index]
        + 1000*[time_breaches[period] for period in time_periods]
            ), "Total Charging costs + Total Outputs"

    # Charge power constraint
    for period, vehicle in profile_av.index:
        prob += (outputs[period, vehicle]
                 <= ((charger1 + ch_assignment[
                     profile_av.loc[(period, vehicle), 'Session']]
                        * (charger2-charger1)) * gv.TIME_FRACT))

    # Final SOC constraint
    for vehicle in vehicles:
        # Get profile for single vehicle
        vehicle_prof = profile_av.loc[(slice(None), vehicle), 'Battery_Use']
        prob += lpSum(
            [outputs[period, vehicle] * gv.CHARGER_EFF
                for period, vehicle in vehicle_prof.index]
        ) >= - (
            profile.loc[(slice(None), vehicle), 'Battery_Use'].sum()
            + rel_charge[vehicle]  # Initial missing charge
            + battery_cap[vehicle]  # Back to 0% charge
            + next_req.loc[vehicle] - 0.00001
        )

    # Intermediate SOC constraints
    for vehicle in vehicles:
        vehicle_prof = profile_av.loc[(slice(None), vehicle), 'Battery_Use']
        for period in vehicle_prof.index.get_level_values(0):
            cumul_use = profile.loc[(slice(period), vehicle),
                                    'Battery_Use'].sum()
            cumul_profile = profile_av.loc[(slice(period), vehicle),
                                           'Battery_Use']
            prob += lpSum(  # Doesn't go over 100% SOC
                [outputs[period, vehicle] * gv.CHARGER_EFF
                    for period, vehicle in cumul_profile.index]
            ) + cumul_use + rel_charge[vehicle] <= 0.00001
        # Make sure it doesn't go below 0% SOC at every return
        profile_ret = profile[profile['Return'] == 1]
        if vehicle in profile_ret.index.get_level_values('Vehicle_ID'):
            returns = profile_ret.loc[(slice(None), vehicle), 'Battery_Use']
            for period in returns.index.get_level_values(0):
                cumul_use = profile.loc[(slice(period), vehicle),
                                        'Battery_Use'].sum()
                cumul_profile = profile_av.loc[
                    (slice(period), vehicle), 'Battery_Use']
                prob += lpSum(  # Doesn't go below 0% SOC
                    [outputs[period, v] * gv.CHARGER_EFF
                        for period, v in cumul_profile.index]
                ) + cumul_use + rel_charge[vehicle] + battery_cap[vehicle] >= 0

    n = len(time_periods.unique())
    for period in time_periods:
        time_veh = list(profile_av.loc[period].index)
        prob += lpSum(  # Max capacity constraint
            [outputs[period, vehicle] for vehicle in time_veh]) <= (
                1 + time_breaches[period]) * capacity.loc[period] * gv.TIME_FRACT
        prob += lpSum(  # Max number of fast chargers
            [ch_assignment[profile_av.loc[(period, v), 'Session']]
                for v in time_veh]
            ) <= gv.NUM_FAST_CH

    prob.solve()
    print(ca, "Next required charge with breach status:",
          LpStatus[prob.status])
    if prob.status == -1:
        print('Magic!!')
        note += '\nMagic!'
        df = magic_charging(profile, ca, rel_charge)
        opt_level = 'Magic'
    else:
        opt_level = 'Breach'
        # Get output variables
        charge_output = []
        breaches = []
        for period, vehicle in outputs:
            if prob.status == 1:
                x = outputs[(period, vehicle)].varValue
                y = ch_assignment[
                    profile_av.loc[(period, vehicle), 'Session']].varValue
            else:
                x = 0
                y = 0
            var_output = {
                'from': period,
                'Vehicle_ID': route,
                output_col: x,
                ch_col: y
            }
            charge_output.append(var_output)
        j = 0
        for period in time_periods:
            if time_breaches[period].varValue != 0:
                j += 1
        print(j, 'breaches')
        df = pd.DataFrame.from_records(charge_output).sort_values(
            ['from', 'Vehicle_ID'])
        df.set_index(['from', 'Vehicle_ID'], inplace=True)
        print('Cost:', value(prob.objective))
    return df, note, opt_level


def charge_incomplete(profile, ca, charger1, charger2,
                      capacity, rel_charge):
    """Optimise charging when 100% is unfeasible

    The objective of this function is to deliver as much charge as possible
    without accounting for required final SOC. If this is unfeasible,
    it will go to magic charging.

    Args:
        profile (DataFrame): empty profile of a single day
        ca (str): category to use in optimisation (opt, BAU)
        charger1 (int): slow charger power
        charger2 (int): fast charger power
        capacity (int): max allowed site capacity
        rel_charge (Series): list of intial battery charge state
            relative to full. Index are Vehicle_ID

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
        lowBound=0,
        upBound=charger2 * gv.TIME_FRACT,
        cat="Continuous"
        )
    ch_assignment = LpVariable.dicts(
        "Charger",
        (session for session in sessions),
        cat='Binary'
    )

    # Create the 'prob' variable to contain the problem data
    prob = LpProblem("Multiple_route_scheduling", LpMaximize)

    # Add costs to objective function
    prob += lpSum(
        [outputs[period, vehicle] for period, vehicle in profile_av.index]
        ), "Total Charging"

    # Charge power constraint
    for period, vehicle in profile_av.index:
        prob += outputs[period, vehicle] <= (
            (charger1 + ch_assignment[profile_av.loc[(period, vehicle),
                                      'Session']] * (charger2-charger1))
            * gv.TIME_FRACT)

    # Intermediate SOC constraints
    for vehicle in vehicles:
        vehicle_prof = profile_av.loc[(slice(None), vehicle), 'Battery_Use']
        for period in vehicle_prof.index.get_level_values(0):
            cumul_use = profile.loc[
                (slice(period), vehicle), 'Battery_Use'].sum()
            cumul_profile = profile_av.loc[
                (slice(period), vehicle), 'Battery_Use']
            prob += lpSum(  # Doesn't go over 100% SOC
                [outputs[period, vehicle] * gv.CHARGER_EFF
                    for period, vehicle in cumul_profile.index]
            ) + cumul_use + rel_charge[vehicle] <= 0
            prob += (lpSum(  # Doesn't go below 0% SOC
                [outputs[period, v] * gv.CHARGER_EFF
                    for period, v in cumul_profile.index])
                + cumul_use + rel_charge[vehicle]
                >= (-battery_cap[vehicle] + gv.TIME_FRACT * (charger1
                    + ch_assignment[profile_av.loc[(period, vehicle),
                                    'Session']] * (charger2-charger1))))

    # Max capacity constraint
    n = len(time_periods.unique())
    for period in time_periods:
        time_veh = list(profile_av.loc[period].index)
        prob += (lpSum([outputs[period, vehicle] for vehicle in time_veh])
                 <= capacity.loc[period] * gv.TIME_FRACT)
        prob += lpSum(
            [ch_assignment[profile_av.loc[(period, vehicle), 'Session']]
                for vehicle in time_veh]) <= gv.NUM_FAST_CH

    # Solve and print to the screen
    prob.solve()
    print(ca, "Partial charge status:", LpStatus[prob.status])
    if prob.status == -1:
        print('Magic!!')
        df = magic_charging(profile, ca, rel_charge)
    else:
        # Get output variables
        charge_output = []
        for period, vehicle in outputs:
            if prob.status == 1:
                x = outputs[(period, vehicle)].varValue
                y = ch_assignment[profile_av.loc[(period, vehicle),
                                                 'Session']].varValue
            else:
                x = 0
            var_output = {
                'from': period,
                'Vehicle_ID': vehicle,
                output_col: x,
                ch_col: y
            }
            charge_output.append(var_output)

        df = pd.DataFrame.from_records(charge_output).sort_values(
            ['from', 'Vehicle_ID'])
        df.set_index(['from', 'Vehicle_ID'], inplace=True)
        print('Cost:', value(prob.objective))
    return df


def magic_charging(profile, ca, rel_charge):
    """Special charging profile

    This chargign doesn't account for site capacity, charger power,
    state of charge. It simply deliveres the charge required to go back
    to 100%, at equal power in all available time periods.

    Args:
        profile (DataFrame): empty profile of all vehicles in all time periods
        ca (str): category to use in optimisation (opt, BAU)
        rel_charge (Series): list of intial battery charge state
            relative to full. Index are Vehicle_ID

    Returns:
        DataFrame: outputs for each vehicle / Time period
    """
    profile_av = profile[profile['Available'] == 1].copy()
    output_col = gv.CAT_COLS['OUTPUT'][ca]
    vehicles = profile.index.get_level_values(1).unique()
    time_periods = profile_av.index.get_level_values(0).unique()
    required_energy = (profile['Battery_Use'].groupby('Vehicle_ID').sum()
                       + rel_charge)
    num_timeperiods = profile_av['Available'].groupby('Vehicle_ID').count()
    req_output = -required_energy/(gv.CHARGER_EFF * num_timeperiods)
    profile_av[output_col] = 0
    for idx in profile_av.index:
        profile_av.loc[idx, output_col] = req_output.loc[idx[1]]
    return profile_av[[output_col]]


def linear_optimiser_V6(profile, ca, charger1, charger2,
                        capacity, rel_charge, next_req, battery_cap):
    """Linear optimisation for a single day charging, mixed fleet

    This optimiser uses PuLP to find optimal power outputs over a day.
    Uses 2 different charger powers, and a varying site capacity.
    Objective: reduce overall electricity spend
    Constraint 1: get to 100% final SOC before end of time period
        of next day departures
    Constraint 2: not go below 0% or over 100% battery charge
    Constraint 3: not go over site capacity
    If this is unfeasible, it will atempt to charge as much as possible
    using incomplete_charge.

    Args:
        profile (DataFrame): empty profile of a single day
        ca (str): category to use in optimisation (opt, BAU)
        charger1 (int): slow charger power
        charger2 (int): fast charger power
        capacity (Series): max allowed site capacity per time period
        rel_charge (Series): list of intial battery charge state
            relative to full. Index are Vehicle_ID
        next_req (Series): battery requirements for next day per vehicle
        battery_cap (dict): dictionary of vehicle ID and their capacity

    Returns:
        DataFrame: Outputs for each time period
        LpProblem: variables, objective and constraints
        Series: end of day final SOC for each vehicle
        str: a note on outcomes of the daily optimisation
        opt_level (str): the level of optimisation that was feasible
    """
    #print(profile)
    vehicles = profile.index.get_level_values(1).unique()
    #print(profile.loc[profile['Return'] == 1])
    
    profile_av = profile[profile['Available'] == 1]
    time_periods = profile_av.index.get_level_values(0).unique()
    price_col = gv.CAT_COLS['PRICE'][ca]
    prices = profile.loc[(time_periods, vehicles[0]), price_col].values
    
    #print(price_col)
    output_col = gv.CAT_COLS['OUTPUT'][ca]
    ch_col = gv.CAT_COLS['CH_TYPE'][ca]
    
    
    sessions = profile['Session'].unique()
    # print(sessions)
    #print(sessions)
    # Define output variable
    outputs = LpVariable.dicts(
        "output",
        ((period, vehicle) for period, vehicle in profile.index),
        lowBound=0,
        upBound=charger2 * gv.TIME_FRACT,
        cat="Continuous")
    ch_assignment = LpVariable.dicts(
        "Charger",
        (session for session in sessions),
        cat='Binary')
    battery = LpVariable.dicts(
        "battery",
        (i for i in range(len(time_periods))),
        lowBound=0,
        upBound=0,
        cat='Continuous'
    )
    note = ''
    # Create the 'prob' variable to contain the problem data
    prob = LpProblem("Multiple_route_scheduling", LpMinimize) 
    #print(outputs)
    #print(prices)
    # Add costs to objective function
    prob += lpSum(
        [(profile_av.loc[(period, vehicle), price_col]
         * (outputs[period, vehicle]) for period, vehicle in profile_av.index)
         + battery[i] * prices[i] for i in range(0, len(prices))
        ]), "Total_Charging_costs"

    #print(prob)
    # for period in profile_av.index:
    prob += lpSum(battery) >= 0
    prob += lpSum(battery) <= 100
    i = 0
    for per in time_periods:
        time_veh = list(profile_av.loc[per].index)
        prob += -battery[i] <= lpSum([outputs[per, vehicle] for vehicle in time_veh])
        i += 1

    # Charge power constraint
    for period, vehicle in profile_av.index:
        prob += outputs[period, vehicle] <= ((
            charger1 + ch_assignment[
                profile_av.loc[(period, vehicle), 'Session']]
            * (charger2-charger1)) * gv.TIME_FRACT)
    # Final SOC constraint
    for vehicle in vehicles:
        # Get profile for single vehicle
        vehicle_prof = profile_av.loc[(slice(None), vehicle), 'Battery_Use']
        prob += lpSum([outputs[period, vehicle] * gv.CHARGER_EFF
                      for period, vehicle in vehicle_prof.index]) == - (
            profile.loc[(slice(None), vehicle), 'Battery_Use'].sum()
            + rel_charge[vehicle])  # Initial missing charge
    # Intermediate SOC constraints
    for vehicle in vehicles:
        vehicle_prof = profile_av.loc[(slice(None), vehicle), 'Battery_Use']
        for period in vehicle_prof.index.get_level_values(0):
            cumul_use = profile.loc[(slice(period), vehicle),
                                    'Battery_Use'].sum()
            cumul_profile = profile_av.loc[(slice(period), vehicle),
                                           'Battery_Use']
            prob += lpSum(  # Doesn't go over 100% SOC
                [outputs[period, vehicle] * gv.CHARGER_EFF
                    for period, vehicle in cumul_profile.index]
            ) + cumul_use + rel_charge[vehicle] <= 0.00001
        # Make sure it doesn't go below 0% SOC at every return
        profile_ret = profile[profile['Return'] == 1]
        #print(profile_ret)
        if vehicle in profile_ret.index.get_level_values('Vehicle_ID'):
            returns = profile_ret.loc[(slice(None), vehicle),
                                      'Battery_Use']
            for period in returns.index.get_level_values(0):
                cumul_use = profile.loc[(slice(period), vehicle),
                                        'Battery_Use'].sum()
                cumul_profile = profile_av.loc[
                    (slice(period), vehicle), 'Battery_Use']
                prob += lpSum(  # Doesn't go below 0% SOC
                    [outputs[period, v] * gv.CHARGER_EFF
                        for period, v in cumul_profile.index]
                ) + cumul_use + rel_charge[vehicle] + battery_cap[vehicle] >= 0

    n = len(time_periods.unique())
    for idx, period in enumerate(time_periods):
        time_veh = list(profile_av.loc[period].index)
        prob += lpSum(  # limits the overall site capacity
            [outputs[period, vehicle] for vehicle in time_veh] + battery[idx]) <= (
                capacity.loc[period] * gv.TIME_FRACT)
        prob += lpSum(  # limits the number of fast chargers
            [ch_assignment[profile_av.loc[(period, v), 'Session']]
                for v in time_veh]) <= gv.NUM_FAST_CH

    # Solve and print to the screen
    prob.solve(PULP_CBC_CMD(msg=False))
    #print(ca, "status:", LpStatus[prob.status])
    # If unfeasible, tries to charge to next day
    if prob.status == -1:
        print("=========================================")
        # df = magic_charging(profile, ca, rel_charge)
        df, note2, opt_level = charge_tonextday(
            profile, ca, charger1, charger2, capacity,
            rel_charge, next_req, battery_cap)
        note += '\nMain unfeasible'
        note += note2
    else:
        # Get output variables
        charge_output = []
        for period, vehicle in outputs:
            if prob.status == 1:
                x = outputs[(period, vehicle)].varValue
                y = ch_assignment[
                    profile.loc[(period, vehicle), 'Session']].varValue
            else:
                x = 0
            var_output = {
                'from': period,
                'Vehicle_ID': vehicle,
                output_col: x,
                ch_col: y
            }
            charge_output.append(var_output)
        bat_output = []
        for bat, time in zip(battery, time_periods):
            if prob.status == 1:
                x = battery[bat].varValue
            else:
                x = 0
            var_output = {
                'from': time,
                'Battery_ID': bat,
                output_col: x,
            }
            bat_output.append(var_output)
        
        opt_level = 'Main'
        df = pd.DataFrame.from_records(charge_output).sort_values(
            ['from', 'Vehicle_ID'])
        df.set_index(['from', 'Vehicle_ID'], inplace=True)
        dfb = pd.DataFrame.from_records(bat_output).sort_values(
            ['from', 'Battery_ID']
        )
        
    # Generate a final SoC array
    final_soc = (rel_charge + (
        df.groupby('Vehicle_ID').sum()[output_col]*gv.CHARGER_EFF
        + profile.groupby('Vehicle_ID').sum()['Battery_Use'])).round(6)
    return df, prob, final_soc, note, opt_level, dfb
