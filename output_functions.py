# Output functions for smart charging algorithm
# Cloned from Phase 1 on 26 October 2020
# Sofia Taylor, Flexible Power Systems

import numpy as np
import global_variables as gv
import pandas as pd
import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as font_manager
import plotly.graph_objects as go
import plotly.io as pio
import os


def summary_outputs(profile, journeys, cap, status, veh='Vivaro_LR'):
    """Creates summary columns and dataframes from outputs

    Args:
        profile (DataFrame): output/SOC per time period, per vehicle
        journeys (DataFrame): all the journey information for all routes
        cap (float): max. site capacity
        status (DataFrame): level of optimisation for each day
        veh (DataFrame): vehicle in use

    Returns:
        DataFrames: dfs corresponding to overall profile, site
            site aggregation, day summary and global summary.
    """
    cols = gv.CAT_COLS
    battery_cap = gv.VSPEC[veh]['C']
    vehicles = profile.index.get_level_values(1).unique()
    range_profile = profile.fillna(0)
    for ca in gv.CATS:
        range_profile[cols['CHARGE_DEL'][ca]] = (
            range_profile[cols['OUTPUT'][ca]]
            * gv.CHARGER_EFF)
        range_profile[cols['ECOST'][ca]] = (
            range_profile[cols['OUTPUT'][ca]]
            * range_profile[cols['PRICE']['opt']])
        for vehicle in vehicles:
            range_profile.loc[(slice(None), vehicle), cols['SOC'][ca]] = (
                battery_cap
                + range_profile.loc[
                    (slice(None), vehicle), cols['CHARGE_DEL'][ca]].cumsum()
                + range_profile.loc[
                    (slice(None), vehicle), 'Battery_Use'].cumsum()
                )*100/battery_cap

    # Sum all vehicles, per time period
    site = range_profile.groupby(level=0).sum()
    site[cols['PRICE']['opt']] = range_profile[
        cols['PRICE']['opt']].groupby(level=0).mean()
    site.drop(columns=[cols['PRICE']['BAU']], inplace=True)
    for ca in gv.CATS:
        site[cols['SOC'][ca]] = range_profile[cols['SOC'][ca]].groupby(
            level=0).mean()
        site[cols['NUM'][ca]] = range_profile[cols['OUTPUT'][ca]].astype(
            bool).groupby(level=0).sum()
        site[cols['BREACH'][ca]] = site[cols['OUTPUT'][ca]] > (
            cap * gv.TIME_FRACT+0.01)

    # Daily summaries
    site['date'] = site.index.date - (
        site.index.time < gv.CHAR_ST).astype(int) * dt.timedelta(days=1)
    day_summary = site.groupby('date').sum()
    day_summary.drop(columns=[cols['PRICE']['opt'], 'Available'], inplace=True)
    day_summary = day_summary.merge(status, left_index=True, right_index=True)
    for ca in gv.CATS:
        day_summary.drop(columns=[cols['NUM'][ca], cols['SOC'][ca]],
                         inplace=True)
    # day_summary['%BAU'] = 100 * (
    #     day_summary['ECost_BAU'] - day_summary['ECost_Opt']
    #     )/day_summary['ECost_BAU']
    # day_summary['%BAU2'] = 100 * (
    #     day_summary['ECost_BAU2'] - day_summary['ECost_Opt']
    #     )/day_summary['ECost_BAU2']

    # Clean to only optimal days
    # clean_summary = day_summary.copy()
    # for ca in gv.CATS:
    #     clean_summary = clean_summary[
    #         clean_summary[gv.CAT_COLS['OUTPUT'][ca]] != 0]
    global_summary = day_summary.sum()
    for ca in gv.CATS:
        global_summary.drop(labels=gv.CAT_COLS['LEVEL'][ca],
                            inplace=True)
    global_summary = global_summary.append(
        day_summary.groupby(
            gv.CAT_COLS['LEVEL'][gv.CATS[0]]).count()['Battery_Use'])
    # c = gv.CATS[0]
    # global_summary[gv.CAT_COLS['LEVEL'][c]] = day_summary.groupby(
    #     c).agg({'BAU':'count'}).T
    # global_summary['%BAU'] = 100 * (
    #     global_summary['ECost_BAU'] - global_summary['ECost_Opt']
    #     )/global_summary['ECost_BAU']
    # global_summary['%BAU2'] = 100 * (
    #     global_summary['ECost_BAU2'] - global_summary['ECost_Opt']
    #     )/global_summary['ECost_BAU2']
    return range_profile, site, day_summary, global_summary


def summary_plot(site_summary):
    """Creates summary plots

    Args:
        site_summary (DataFrame): aggregated profile for the whole site

    Returns:
        fig
    """
    fig, axs = plt.subplots(
        5,
        figsize=(12, 10),
        sharex=True,
        gridspec_kw={'hspace': 0.1})

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
        axs[3].plot(
            x,
            site_summary[cols['SOC'][ca]],
            label=gv.LABELS[ca],
            color=gv.COLOR[ca])

    axs[4].plot(x,
                site_summary[cols['PRICE']['opt']],
                label='Eletricity_price', color=gv.FPS_PURPLE)

    # labels and legends
    axs[0].set_ylabel('E. Demand (kW)', color=gv.FPS_BLUE, fontweight='bold')
    axs[1].set_ylabel('# Charging', color=gv.FPS_BLUE, fontweight='bold')
    axs[2].set_ylabel('E. Costs (GBP)', color=gv.FPS_BLUE, fontweight='bold')
    # axs[3].set_ylabel('SOC (%)',color=gv.FPS_BLUE, fontweight='bold')
    axs[4].set_ylabel('E. Price (p/kWh)', color=gv.FPS_BLUE, fontweight='bold')
    axs[4].set_xlabel('Time', color=gv.FPS_BLUE, fontweight='bold')
    axs[0].legend(frameon=False)

    for ax in fig.get_axes():
        ax.xaxis.set_major_locator(plt.MaxNLocator(10))
    return fig


def daily_summary_plot(summary):
    """Create plot of features per day in a range

    Args:
        summary (DataFrame): daily summary

    Returns:
        fig
    """
    fig, axs = plt.subplots(
        2,
        figsize=(12, 10),
        sharex=True,
        gridspec_kw={'hspace': 0.1})

    x = summary.index
    cats = gv.CATS
    cols = gv.CAT_COLS
    axs[0].plot(
        x,
        summary[cols['OUTPUT'][gv.CATS[0]]]/gv.TIME_FRACT,
        label=gv.LABELS[gv.CATS[0]],
        color='tab:red'
        )
    for ca in cats:
        axs[1].scatter(
            x,
            summary[cols['ECOST'][ca]]/100,
            label=ca,
            color=gv.COLOR[ca]
        )

    # labels and legends
    axs[0].set_ylabel('E. Demand (kW)', color=gv.FPS_BLUE, fontweight='bold')
    axs[1].set_ylabel('E. Costs (GBP)', color=gv.FPS_BLUE, fontweight='bold')
    #axs[2].set_ylabel('Savings (%)', color=gv.FPS_BLUE, fontweight='bold')
    axs[1].set_xlabel('Time', color=gv.FPS_BLUE, fontweight='bold')
    axs[1].legend(frameon=False)
    # axs[2].legend(frameon=False)

    for ax in fig.get_axes():
        ax.xaxis.set_major_locator(plt.MaxNLocator(12))
    return fig


def summary_BAU_plot(site_summary):
    """Dumb charging plot

    Args:
        site_summary (DataFrame): site profile aggregation

    Returns:
        fig
    """
    fig, axs = plt.subplots(2,
                            figsize=(5, 4),
                            sharex=True,
                            gridspec_kw={'hspace': 0.1})
    x = site_summary.index.strftime('%H:%M')
    cats = ['BAU', 'BAU2']
    cols = gv.CAT_COLS

    for ca in cats:
        axs[0].plot(x, site_summary[cols['OUTPUT'][ca]], color=gv.COLOR[ca])
        # axs[1].plot(x, site_summary[cols['SOC'][ca]],color=gv.COLOR[ca])

    axs[0].set_ylabel('Site output (kW)')
    axs[1].set_ylabel('SoC (%)')
    axs[1].set_xlabel('Time')
    axs[0].set_title('BAU profile')
    axs[0].xaxis.set_major_locator(plt.MaxNLocator(10))
    axs[0].legend(['Unconstrained', 'Constrained'], frameon=False)
    return fig


def scatter_plot(site_summary):
    """Scatter plot of electricity price in each scenario

    Args:
        site_summary (DataFrame): site profile aggregation

    Returns:
        fig
    """
    fig, axs = plt.subplots(1, figsize=(8, 4))

    x = site_summary.groupby('Electricity_Price').mean().index
    y1 = site_summary.groupby('Electricity_Price').sum()
    cols = [gv.CAT_COLS['OUTPUT'][ca] for ca in gv.CATS]
    y1[cols] = y1[cols].replace({0: np.nan})

    for ca in gv.CATS:
        axs.scatter(
            x,
            y1[gv.CAT_COLS['OUTPUT'][ca]],
            color=gv.COLOR[ca],
            alpha=gv.ALPHA[ca],
            label=gv.LABELS[ca]
            )

    axs.set_ylabel('Output (kWh)')
    axs.set_xlabel('Electricity Price (p / kWh)')
    axs.xaxis.set_major_locator(plt.MaxNLocator(10))
    axs.legend(frameon=False)
    return fig


def histograms_journeys(day_journeys, min_time, max_time):
    num_bins = int((max_time - min_time).total_seconds()
                   / (gv.TIME_INT.total_seconds()) + 1)
    bins_time = [min_time + i * gv.TIME_INT for i in range(num_bins)]

    fig, ax = plt.subplots(
        1,
        figsize=(6, 2))
    ax.hist(
        day_journeys['Start_Time_of_Route'],
        bins=bins_time,
        color=gv.FPS_BLUE,
        alpha=0.6,
        label='Departures')
    ax.hist(
        day_journeys['End_Time_of_Route'],
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


def create_daily_summary(summary, day):
    """Takes a single day from site summary data

    Args:
        summary (DataFrame): table of site consumption/SOC for each
            time period
        day (datetime): day to select

    Returns:
        DataFrame: profile for a single day
    """
    start_datetime = day + gv.CHAR_ST_DELTA
    end_datetime = start_datetime + dt.timedelta(days=1)
    day_profile = summary[(summary.index < end_datetime)
                          & (summary.index >= start_datetime)]
    day_profile.sort_index(inplace=True)
    return day_profile

def fig_scenario_count(df, x):
    """Creates a figure for feasible/unfeasible distribution

    Args:
        df (DataFrame): table of feasible and unfeasible journeys with
                        MultiIndex ['cap','Slow_ch','Fast_c']. Same
                        order as x
        x (list): List of charger combinations, in same order as df

    Returns:
        fig: stacked bar chart
    """
    categories = df.columns
    caps = df.index.get_level_values('cap').unique()
    fig, axs = plt.subplots(
        5,
        figsize=(6,6),
        sharex=True,
        gridspec_kw={'hspace':0.1})
    for i in range(5):
        axs[i].bar(
            x, df.loc[caps[i]]['Feasible'],
            label="Feasible")
        axs[i].bar(
            x, df.loc[caps[i]]['Unfeasible'],
            bottom=(df.loc[caps[i]]['Feasible']),
            label='Unfeasible')

        axs[i].set_ylabel('{} kW \n# days'.format(caps[i]), color=gv.FPS_BLUE)
    axs[-1].legend()
    axs[-1].set_xlabel('Combination of chargers', color=gv.FPS_BLUE)
    axs[0].set_title(
        'Distribution of scenarios for each combination of chargers',
        color=gv.FPS_BLUE, fontweight='bold')
    return fig

def createHeatmap(profile, desc="", zrange=[0,100]):
    """Generate heatmaps for charging schedules

    Args:
        profile (DataFrame): Profile aggregated at site level
        desc (str): description to include in tite

    Returns:
        fig: heatmap
    """
    profile['day'] = profile.index.date
    profile['time'] = profile.index.time
    dates = profile['date'].unique()
    timeperiods = np.sort(profile['time'].unique())

    loads = np.zeros((len(timeperiods), len(dates)))

    for i, date in enumerate(dates):
        for j, tp in enumerate(timeperiods):
            fulldt = dt.datetime.combine(date, tp)
            if fulldt in profile.index:
                loads[j, i] = 2*profile.loc[
                    fulldt, gv.CAT_COLS['OUTPUT'][gv.CATS[0]]]

    # use loads, dates, and timeperiods as your data
    fig = go.Figure(data=go.Heatmap(
        z=loads,
        y=timeperiods,
        x=dates,
        hoverongaps=False,
        colorbar=dict(title='EV charging (kW)'),
        zmin=zrange[0], zmax=zrange[1]
        ))

    fig.update_layout(
        title="EV Charging schedule from"+str(dates[0])+" to "+str(dates[-1])
        + '\n' + str(desc)
    )
    fig.show()
    return fig

def create_grid_file(path):
    """Creates a csv file with correct headers

    Args:
        path (string): relative file path for grid file
    """
    grid_file = open(path, 'a')
    grid_file.write(
        'run,Branch_ID,Charger 1,Charger 2,Capacity (kW),Runtime,Battery Use,'
    )
    for ca in gv.CATS:
        grid_file.write(str(gv.CAT_COLS['OUTPUT'][ca] + ','))
        grid_file.write(str(gv.CAT_COLS['CHARGE_DEL'][ca] + ','))
        grid_file.write(str(gv.CAT_COLS['ECOST'][ca] + ','))
        grid_file.write(str(gv.CAT_COLS['BREACH'][ca] + ','))
    grid_file.write('Main,Tonext,Breach,Magic,Empty')
    grid_file.write(',Notes')
    grid_file.close()
    return


def write_grid_file(path, run, branch, charger, cap,
                    runtime, global_summary, notes):
    """Write settings and results to the grid file

    Args:
        path (str): relative file path for grid file
    """
    grid_file = open(path, 'a')
    grid_file.write('\n' + str(run) + ',' + str(branch) + ','
                    + str(charger[0]) + ',' + str(charger[1])  + ','
                    + str(cap) + ',')
    grid_file.write(str(runtime) + ',')
    grid_file.write(str(global_summary['Battery_Use']) + ',')

    for ca in gv.CATS:
        grid_file.write(
            str(global_summary[gv.CAT_COLS['OUTPUT'][ca]]) + ',')
        grid_file.write(
            str(global_summary[gv.CAT_COLS['CHARGE_DEL'][ca]]) + ',')
        grid_file.write(
            str(global_summary[gv.CAT_COLS['ECOST'][ca]]) + ',')
        grid_file.write(
            str(global_summary[gv.CAT_COLS['BREACH'][ca]]) + ',')
    for l in gv.LEVELS:
        if l in global_summary.index:
            grid_file.write(str(global_summary[l]) + ',')
        else:
            grid_file.write('0,')
    grid_file.write(notes)
    grid_file.close()
    return

def create_settings_file(run, run_dir, notes, charger, cap, branch,
                         global_summary, bad_days):
    """Create a list of settings

    Args:
        run (int): id. for this script run
        run_dir (str): file path for this run's folder
        notes (str): Any notes generated in the script
        charger (int): list of charger powers (usually 2)
        cap (int): site capacity
        branch (int): branch ID
        global_summary (Series): generated from summary_outputs
        bad_days (str): list of all 'unusual' days and their descript.
    """
    with open('global_variables.py','r') as f:
        global_variables = f.read()

    with open(os.path.join(
        run_dir, 'variables{}.csv'.format(run)),'a') as fi:
        fi.write(notes)
        fi.write('\n' + str(run) + ',' + str(charger) + ',' + str(cap)
                 + str(branch) + '\n')
        fi.write(global_summary.to_string())
        fi.write(bad_days)
        fi.write('\n \n global_variables.py:\n')
        fi.write(global_variables)
        return