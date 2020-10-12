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

# Create function for one route, in one day
def singleroute_BAU_schedule(journeys, day, route, eprice):
    mask = ( (eprice['from'] >= dt.datetime.combine(day, gv.CHAR_ST)) 
    & (eprice['from'] < dt.datetime.combine(day + dt.timedelta(days=1), gv.CHAR_ST)))
    single_profile = eprice[mask][['from','Electricity_Price','Time_Price']].copy()
    single_profile['Route_ID'] = route
    single_profile['Vehicle_ID'] = journeys.loc[(day,route)]['Vehicle_ID']
    return single_profile

def get_daily_data(journeys,day):
    """Get journeys corresponding to a day

    Args:
        journeys (profile): All journeys
        day (datetime):

    Returns:
        DataFrame: The profile corresponding to that day
    """
    if journeys.index.isin([day.date()],level='date').any():
        daily_df = journeys.loc[(day)].copy()
        daily_df.drop(columns=['Branch_ID'], inplace=True)
        daily_df.sort_values(by=['Start_Time_of_Route'], inplace=True)
    else:
        daily_df = pd.DataFrame(columns=['None'])
    return daily_df

def create_day_times(day,eprice):
    """Creates the timeline for a given day with the price information

    Args:
        day (datetime): day to create
        eprice (DataFrame): table with pricing information

    Returns:
        DataFrame: profile for that day
    """
    mask = ( (eprice['from'] >= dt.datetime.combine(day, gv.CHAR_ST)) 
    & (eprice['from'] < dt.datetime.combine(day + dt.timedelta(days=1), gv.CHAR_ST)))
    timeline = eprice[mask][['from','Electricity_Price','Time_Price']].copy()
    timeline['date'] = day
    return timeline

def create_daily_schedule(profile, day):
    """Takes a single day from journey data and makes a schedule

    Args:
        profile (DataFrame): profile for a whole range, all vehicles
        day (datetime):

    Returns:
        DataFrame: profile for that day, sorted
    """
    start_datetime = day + gv.CHAR_ST_DELTA
    end_datetime = start_datetime + dt.timedelta(days=1)
    day_profile = profile[(profile.index.get_level_values(0) < end_datetime)
    & (profile.index.get_level_values(0) >= start_datetime)]
    return day_profile.sort_index()