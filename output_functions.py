# Output functions for smart charging algorithm
import numpy as np
import global_variables as gv
import pandas as pd
import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as font_manager

# Creates summary columns and dataframes from outputs
def summary_outputs(profile, journeys):
    cols=gv.CAT_COLS
    vehicles = journeys.index
    day_profile = profile.copy()
    day_journeys = journeys.copy()
    for ca in gv.CATS:
        day_profile[cols['CHARGE_DEL'][ca]] = (
            day_profile[cols['OUTPUT'][ca]] 
            * gv.CHARGER_EFF)
        day_profile[cols['ECOST'][ca]] = (
            day_profile[cols['OUTPUT'][ca]] 
            * day_profile[cols['PRICE']['opt']])
        
        for vehicle in vehicles:
            opt = (gv.BATTERY_CAPACITY - journeys.loc[vehicle,'Energy_Required'] 
            + day_profile.loc[(slice(None),vehicle),cols['CHARGE_DEL'][ca]].cumsum())*100 / gv.BATTERY_CAPACITY
            day_profile.loc[(slice(None),vehicle),cols['SOC'][ca]] = opt

        day_journeys[cols['OUTPUT'][ca]] = day_profile[cols['OUTPUT'][ca]].groupby(level=1).sum()
        day_journeys[cols['ECOST'][ca]] = day_profile[cols['ECOST'][ca]].groupby(level=1).sum()
        day_journeys[cols['PEAK'][ca]] = day_profile[cols['OUTPUT'][ca]].groupby(level=1).max()

    site = day_profile.groupby(level=0).sum()
    site[cols['PRICE']['opt']] = day_profile[cols['PRICE']['opt']].groupby(level=0).mean()
    for ca in gv.CATS:
        site[cols['SOC'][ca]] = day_profile[cols['SOC'][ca]].groupby(level=0).mean()
        site[cols['NUM'][ca]] = day_profile[cols['OUTPUT'][ca]].astype(bool).groupby(level=0).sum()
    site.drop(columns=[cols['PRICE']['BAU'], 'Vehicle_ID'], inplace=True)

    global_summary = site.sum()
    global_summary.drop(labels=[cols['PRICE']['opt']], inplace=True)
    for ca in gv.CATS:
        global_summary.drop(labels=[cols['SOC'][ca],cols['NUM'][ca]], inplace=True)
    return day_profile, day_journeys, site, global_summary

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
        axs[1].plot(x, site_summary[cols['NUM'][ca]], label=ca, color=gv.COLOR[ca])
        axs[2].plot(x, site_summary[cols['ECOST'][ca]]/100, label=ca, color=gv.COLOR[ca])
        axs[3].plot(
            x, 
            site_summary[cols['SOC'][ca]], 
            label=gv.LABELS[ca], 
            color=gv.COLOR[ca])

    axs[4].plot(x, 
    site_summary[cols['PRICE']['opt']], 
    label='Eletricity_price', 
    color=gv.FPS_PURPLE)

    # labels and legends
    axs[0].set_ylabel('E. Demand (kW)',color=gv.FPS_BLUE, fontweight='bold')
    axs[1].set_ylabel('# Charging',color=gv.FPS_BLUE, fontweight='bold')
    axs[2].set_ylabel('E. Costs (GBP)',color=gv.FPS_BLUE, fontweight='bold')
    axs[3].set_ylabel('SOC (%)',color=gv.FPS_BLUE, fontweight='bold')
    axs[4].set_ylabel('E. Price (p/kWh)',color=gv.FPS_BLUE, fontweight='bold')
    axs[4].set_xlabel('Time',color=gv.FPS_BLUE, fontweight='bold')
    axs[0].legend(frameon=False)


    for ax in fig.get_axes():
        ax.xaxis.set_major_locator(plt.MaxNLocator(10))
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