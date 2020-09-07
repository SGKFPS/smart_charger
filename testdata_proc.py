# Data processing functions for testing optimiser
# Started 1 Sept 2020

import numpy as np
from numpy.core.fromnumeric import shape
import pandas as pd
import datetime as dt
import glob
import pickle
import global_variables as gv
import functions as f
from global_variables import NUM_VEHICLES

def prep_data(path):
    all_files = glob.glob(path)
    import_cols = ['Route_ID', 'Branch_ID', 'Start_Time_of_Route',
                'End_Time_of_Route', 'Planned_total_Mileage'] #FIXME add to gv

    journeys = pd.concat((pd.read_csv(f,usecols=import_cols) for f in all_files))
    journeys['Start_Time_of_Route']=pd.to_datetime(journeys['Start_Time_of_Route'])
    journeys['date'] = journeys['Start_Time_of_Route'].dt.date
    journeys = limit_vehicles(journeys)
    journeys['Start_Time_of_Route'] = journeys['Start_Time_of_Route'].dt.time
    journeys['End_Time_of_Route']=pd.to_datetime(journeys['End_Time_of_Route'])
    journeys['End_Time_of_Route'] = journeys['End_Time_of_Route'].dt.time

    # Calculate journey requirements and add randomness
    journeys['Required_SOC'] = journeys['Planned_total_Mileage']*gv.POWER_KM*(1
                                + gv.REFR_RATIO 
                                + gv.RANDOM_SOC_RATIO* np.random.uniform(size=
                                journeys.shape[0]))
    journeys.set_index(['date','Vehicle_ID'],inplace=True)
    return journeys

def limit_vehicles(journeys):
    # FIXME this moving back and forth from numpy/pandas is not good.
    list_days = list(journeys.date.unique())
    num_days = len(list_days)
    num_columns = journeys.shape[1]
    np_journeys = np.empty(shape = (gv.NUM_VEHICLES * num_days, num_columns + 1),dtype=object)
    print(np.shape(np_journeys))
    for i in range(num_days):
        daily_journeys = journeys[journeys['date'] == list_days[i]].head(gv.NUM_VEHICLES).to_numpy()
        N = min([len(daily_journeys), gv.NUM_VEHICLES])
        np_journeys[NUM_VEHICLES*i:NUM_VEHICLES*i+N,:num_columns] = daily_journeys
        np_journeys[NUM_VEHICLES*i:NUM_VEHICLES*(i+1),num_columns] = np.arange(gv.NUM_VEHICLES)
    column_names = journeys.columns.append(pd.Index(['Vehicle_ID']))
    capped_journeys = pd.DataFrame(data=np_journeys, columns=column_names)
    return capped_journeys

def get_weeks_data(journeys, day,delta):
    """Takes a week worth of data (or some period) from the combined dataframe

    Args:
        journeys (DataFrame): dataframe of all journeys in a given period

    Returns:
        week: dataframe containing only the journeys in that week
    """

    week = journeys[(journeys.index.get_level_values('date').date >= day) 
    & (journeys.index.get_level_values('date').date < day + delta)]
    return week

def clean_pricing(path):
    import_cols = ['date', 'from', 'to', 'unit_rate_excl_vat']
    pricing = pd.read_csv(path, usecols=import_cols)
    pricing['from'] = pd.to_datetime(pricing['date'] + " " + pricing['from'])
    pricing['to'] = pd.to_datetime(pricing['date'] + " " + pricing['to'])
    return pricing

all_journeys = prep_data(gv.data_path)
#print(all_journeys.head(20))


prototype_week = get_weeks_data(all_journeys, gv.PROTOTYPE_DAYS[0], gv.TIME_RANGE)
test_week = get_weeks_data(all_journeys, gv.TEST_DAYS[0], gv.TIME_RANGE)
price_data = clean_pricing(gv.pricing_path)
charging_profile = f.dumb_charging(prototype_week, price_data)

# Pickle
pickle.dump(all_journeys,open('Data/all_journeys','wb'))
pickle.dump(prototype_week,open('Data/prototype_week','wb'))
pickle.dump(test_week,open('Data/test_week','wb'))
pickle.dump(price_data,open('Data/price_data','wb'))
pickle.dump(charging_profile,open('Data/BAU_profile','wb'))

#print(prototype_week.head())

print('Start time range:' , 
min(prototype_week['Start_Time_of_Route']), max(prototype_week['Start_Time_of_Route']))

print('End time range:' , 
min(prototype_week['End_Time_of_Route']), max(prototype_week['End_Time_of_Route']))