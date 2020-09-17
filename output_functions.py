# Output functions for smart charging algorithm
import numpy as np
import global_variables as gv
import pandas as pd
import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as font_manager

# Creates summary columns and dataframes from outputs, for multiple days
def summary_outputs(profile, journeys,dates):
    cols=gv.CAT_COLS
    routes = journeys.index.get_level_values(1)
    range_profile = profile.copy()
    range_journeys = journeys.reset_index(level=0)
    last_day = range_journeys.date.unique()[-1]
    range_journeys = range_journeys[range_journeys.date != last_day]
    for ca in gv.CATS:
        range_profile[cols['CHARGE_DEL'][ca]] = (
            range_profile[cols['OUTPUT'][ca]] 
            * gv.CHARGER_EFF)
        range_profile[cols['ECOST'][ca]] = (
            range_profile[cols['OUTPUT'][ca]] 
            * range_profile[cols['PRICE']['opt']])
        # TODO Remove SOC from here, add to optimiser. Add a reasonable SoC for the vehicle summary
        # for route in routes:
            # opt = (gv.BATTERY_CAPACITY - journeys.loc[(slice(None),route),'Energy_Required'] 
            # + range_profile.loc[(slice(None),route),cols['CHARGE_DEL'][ca]].cumsum())*100 / gv.BATTERY_CAPACITY
            # range_profile.loc[(slice(None),route),cols['SOC'][ca]] = opt

        range_journeys[cols['OUTPUT'][ca]] = range_profile[cols['OUTPUT'][ca]].groupby(level=1).sum()
        range_journeys[cols['ECOST'][ca]] = range_profile[cols['ECOST'][ca]].groupby(level=1).sum()
        range_journeys[cols['PEAK'][ca]] = range_profile[cols['OUTPUT'][ca]].groupby(level=1).max()

    # Aggregate per vehicle, time
    veh_profile = range_profile.groupby(['from','Vehicle_ID']).sum()
    veh_profile['Electricity_Price'] = range_profile[['Electricity_Price','Vehicle_ID']].groupby(['from','Vehicle_ID']).mean()
    veh_profile.drop(columns=[cols['PRICE']['BAU']], inplace=True)

    # Sum all vehicles, per time period
    site = veh_profile.groupby(level=0).sum()
    site[cols['PRICE']['opt']] = veh_profile[cols['PRICE']['opt']].groupby(level=0).mean()
    for ca in gv.CATS:
        #site[cols['SOC'][ca]] = day_profile[cols['SOC'][ca]].groupby(level=0).mean()
        site[cols['NUM'][ca]] = veh_profile[cols['OUTPUT'][ca]].astype(bool).groupby(level=0).sum()

    # Daily summaries
    site['date'] = site.index.date - (
        site.index.time < gv.CHAR_ST).astype(int) * dt.timedelta(days=1)
    day_summary = site.groupby('date').sum()
    day_summary.drop(columns=[cols['PRICE']['opt']], inplace=True)
    for ca in gv.CATS:
        day_summary.drop(columns=[cols['NUM'][ca]], inplace=True)
    day_summary['%BAU'] = 100 * (
        day_summary['ECost_BAU'] - day_summary['ECost_Opt']
        )/day_summary['ECost_BAU']
    day_summary['%BAU2'] = 100 * (
        day_summary['ECost_BAU2'] - day_summary['ECost_Opt']
        )/day_summary['ECost_BAU2']

    global_summary = day_summary.sum()
    global_summary['%BAU'] = 100 * (
        global_summary['ECost_BAU'] - global_summary['ECost_Opt']
        )/global_summary['ECost_BAU']
    global_summary['%BAU2'] = 100 * (
        global_summary['ECost_BAU2'] - global_summary['ECost_Opt']
        )/global_summary['ECost_BAU2']
    return range_profile, range_journeys, veh_profile, site, day_summary, global_summary

# Creates summary plot
def summary_plot(site_summary):
    fig, axs = plt.subplots(5,
    figsize=(12,10),
    sharex=True, 
    gridspec_kw={'hspace':0.1})

    x = site_summary.index.strftime('%H:%M')
    cats = gv.CATS
    cols = gv.CAT_COLS

    for ca in cats:
        axs[0].plot(
            x, 
            site_summary[cols['OUTPUT'][ca]]*2, 
            label=gv.LABELS[ca], 
            color=gv.COLOR[ca]
            )
        axs[1].plot(
            x, 
            site_summary[cols['NUM'][ca]], 
            label=ca, 
            color=gv.COLOR[ca])
        axs[2].plot(
            x, 
            site_summary[cols['ECOST'][ca]]/100, 
            label=ca, 
            color=gv.COLOR[ca])
        # axs[3].plot(
        #     x, 
        #     site_summary[cols['SOC'][ca]], 
        #     label=gv.LABELS[ca], 
        #     color=gv.COLOR[ca])

    axs[4].plot(x, 
    site_summary[cols['PRICE']['opt']], 
    label='Eletricity_price', 
    color=gv.FPS_PURPLE)

    # labels and legends
    axs[0].set_ylabel('E. Demand (kW)',color=gv.FPS_BLUE, fontweight='bold')
    axs[1].set_ylabel('# Charging',color=gv.FPS_BLUE, fontweight='bold')
    axs[2].set_ylabel('E. Costs (GBP)',color=gv.FPS_BLUE, fontweight='bold')
    #axs[3].set_ylabel('SOC (%)',color=gv.FPS_BLUE, fontweight='bold')
    axs[4].set_ylabel('E. Price (p/kWh)',color=gv.FPS_BLUE, fontweight='bold')
    axs[4].set_xlabel('Time',color=gv.FPS_BLUE, fontweight='bold')
    axs[0].legend(frameon=False)


    for ax in fig.get_axes():
        ax.xaxis.set_major_locator(plt.MaxNLocator(10))
    return fig

# Create plot of features per day in a range
def daily_summary_plot(summary):
    fig, axs = plt.subplots(
        3,
        figsize=(12,10),
        sharex=True, 
        gridspec_kw={'hspace':0.1})

    x = summary.index
    cats = gv.CATS
    cols = gv.CAT_COLS
    axs[0].plot(
        x, 
        summary[cols['OUTPUT']['opt']]/gv.TIME_FRACT, 
        label=gv.LABELS['opt'], 
        color='tab:red'
        )
    for ca in cats:
        axs[1].plot(
            x,
            summary[cols['ECOST'][ca]]/100,
            label=ca,
            color=gv.COLOR[ca]
        )
    axs[2].plot(
        x,
        summary['%BAU'],
        label='BAU',
        color=gv.COLOR['BAU']
    )
    axs[2].plot(
        x,
        summary['%BAU2'],
        label='BAU2',
        color=gv.COLOR['BAU2']
    )

    # labels and legends
    axs[0].set_ylabel('E. Demand (kW)',color=gv.FPS_BLUE, fontweight='bold')
    axs[1].set_ylabel('E. Costs (GBP)',color=gv.FPS_BLUE, fontweight='bold')
    axs[2].set_ylabel('Savings (%)',color=gv.FPS_BLUE, fontweight='bold')
    axs[2].set_xlabel('Time',color=gv.FPS_BLUE, fontweight='bold')
    axs[1].legend(frameon=False)
    axs[2].legend(frameon=False)

    for ax in fig.get_axes():
        ax.xaxis.set_major_locator(plt.MaxNLocator(12))
    return fig
    
# Save BAU profile

def summary_BAU_plot(site_summary):
    fig, axs = plt.subplots(2,
    figsize=(5,4),
    sharex=True,
    gridspec_kw={'hspace':0.1})
    x = site_summary.index.strftime('%H:%M')
    cats = ['BAU','BAU2']
    cols = gv.CAT_COLS

    for ca in cats:
        axs[0].plot(x, site_summary[cols['OUTPUT'][ca]],color=gv.COLOR[ca])
        axs[1].plot(x, site_summary[cols['SOC'][ca]],color=gv.COLOR[ca])

    axs[0].set_ylabel('Site output (kW)')
    axs[1].set_ylabel('SoC (%)')
    axs[1].set_xlabel('Time')
    axs[0].set_title('BAU profile')
    axs[0].xaxis.set_major_locator(plt.MaxNLocator(10))
    axs[0].legend(['Unconstrained','Constrained'], frameon=False)
    return fig

# Save scatter plot
def scatter_plot(site_summary):
    fig, axs = plt.subplots(1,figsize=(8,4))

    x = site_summary.groupby('Electricity_Price').mean().index
    y1 = site_summary.groupby('Electricity_Price').sum()
    cols=['Output_BAU','Output_BAU2','Output_Opt']
    y1[cols] = y1[cols].replace({0:np.nan})

    axs.scatter(
        x, 
        y1['Output_Opt'],
        color=gv.COLOR['opt'],
        alpha=1,
        label='Smart Charging'
        )
    axs.scatter(
        x, 
        y1['Output_BAU'],
        color=gv.COLOR['BAU'],
        alpha=0.6,
        label='Unconstrained BAU'
        )
    axs.scatter(
        x, 
        y1['Output_BAU2'],
        color=gv.COLOR['BAU2'],
        alpha=0.6,
        label='Constrained BAU'
        )

    axs.set_ylabel('Output (kWh)')
    axs.set_xlabel('Electricity Price (p / kWh)')
    axs.xaxis.set_major_locator(plt.MaxNLocator(10))
    axs.legend(frameon=False)
    return fig

# plot histograms
def histograms_journeys(day_journeys, min_time, max_time):
    num_bins = int(
        (max_time - min_time).total_seconds() / (gv.TIME_INT.total_seconds()) 
        + 1)
    bins_time = [min_time + i * gv.TIME_INT for i in range(num_bins)]

    fig, ax = plt.subplots(1,
    figsize=(6,2))
    ax.hist(day_journeys['Start_Time_of_Route'], 
    bins=bins_time,
    color=gv.FPS_BLUE,
    alpha=0.6,
    label='Departures')
    ax.hist(day_journeys['End_Time_of_Route'], 
    bins=bins_time,
    color=gv.FPS_GREEN,
    alpha=0.6,
    label='Arrivals')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H'))
    ax.legend(frameon=False)
    ax.set_xlabel('Time interval', color=gv.FPS_BLUE, fontweight='bold')
    ax.set_ylabel('# Vehicles', color=gv.FPS_BLUE, fontweight='bold')
    plt.show()
    return fig

# Takes a single day from journey data and makes a schedule
def create_daily_summary(summary, day):
    start_datetime = day + gv.CHAR_ST_DELTA
    end_datetime = start_datetime + dt.timedelta(days=1)
    day_profile = summary[(summary.index < end_datetime)
    & (summary.index >= start_datetime)]
    day_profile.sort_index(inplace=True)
    return day_profile