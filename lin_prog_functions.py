# Stores all prototypoe linear_optimiser functions

import numpy as np
import global_variables as gv
import pandas as pd
import datetime as dt
from pulp import *

def linear_optimiser_V1(profile,journeys,ca):
    price_col = gv.CAT_COLS['PRICE'][ca]
    output_col = gv.CAT_COLS['OUTPUT'][ca]
    # Define output variable
    outputs = LpVariable.dicts("output",
    ((period, route) for period, route in profile.index),
    lowBound = 0,
    upBound = gv.CHARGER_POWER * gv.TIME_FRACT,
    cat = "Continuous"
    )

    # Create the 'prob' variable to contain the problem data
    prob = LpProblem("Multiple_route_scheduling",LpMinimize)

    # Add costs to objective function

    prob += lpSum(
        [profile.loc[(period, route), price_col] * outputs[period, route] for period, route in profile.index]
        ), "Total Charging costs"

    # Final SOC constraint
    time_period = profile.index.get_level_values(0)
    routes = profile.index.get_level_values(1)
    vehicles = journeys['Vehicle_ID'].unique()

    for vehicle in vehicles:
        vehicle_profile = profile[profile['Vehicle_ID'] == vehicle]
        prob += lpSum(
            [outputs[period, route] for period, route in vehicle_profile.index]) == journeys[journeys['Vehicle_ID'] == vehicle]['Energy_Required'].sum() / gv.CHARGER_EFF

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
            [outputs[period, route] for route in routes])/n <= gv.SITE_CAPACITY[ca]
    
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