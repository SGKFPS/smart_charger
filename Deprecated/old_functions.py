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