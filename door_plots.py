from functools import lru_cache

from matplotlib import axes as Axes, pyplot as plt, rcParams, checkdep_usetex
from matplotlib.dates import MonthLocator, DateFormatter
from numpy import exp, linspace, log, polyfit, sqrt

from door_stats import *


@lru_cache()
def is_tex_available():
    return checkdep_usetex(True)


@lru_cache()
def percent():
    """
    Ensure percent sign is escaped iff tex is available
    """
    return r"\%" if is_tex_available() else "%"


def plot_openness_by_hour(data: list, period: dict, ax: Axes):
    """
    Plots the openness by hour from the raw data.

    :param data: Raw data
    :param period: Period over which to average the openness
    :param ax: Axes object in which to put the plot
    :return: None
    """
    num_hrs = 24

    # Get data
    hour_bins = get_openness_by_hour(data, period)

    # Plot bar chart
    ax.bar(range(num_hrs + 1), hour_bins)

    # Decorate the axes
    ax.yaxis.grid(True, which="both", linestyle="-.")
    ax.set_xlim(1, num_hrs)
    ax.set_xticks(range(num_hrs + 1))
    ax.set_xticklabels([f"{t:02d}" for t in ax.get_xticks()])
    ax.set_yticklabels([f"{o * 100:.1f}{percent()}" for o in ax.get_yticks()])
    ax.set_ylabel("p", rotation=0)
    ax.set_xlabel("Tid på døgnet")


def plot_openness(data: list, period: dict, ax: Axes):
    """
    Plots the openness from the raw data.

    :param data: Raw data
    :param period: Period over which to average the openness
    :param ax: Axes object in which to put the plot
    :return: None
    """
    # Get data
    datetimes, openness = get_openness(data, period)

    # Make filled line plot
    ax.fill_between(datetimes, openness)

    # Decorate axes
    ax.xaxis.set_major_locator(MonthLocator((1, 4, 7, 10), bymonthday=1))
    ax.xaxis.set_major_formatter(DateFormatter("%b '%y"))
    ax.set_yticklabels([f"{o * 100:.0f}{percent()}" for o in ax.get_yticks()])
    ax.set_ylabel("p", rotation=0)
    ax.grid(linestyle="-.")


def plot_openness_by_weekday(data: list, period: dict, ax: Axes):
    """
    Plot the openness by weekday from the raw data.

    :param data: Raw data
    :param period: Period over which to average the openness
    :param ax: Axes object in which to put the plot
    :return: None
    """
    week_bins = get_openness_by_weekday(data, period)
    weekday_avg = sum(week_bins[0:5]) / 5
    weekend_avg = sum(week_bins[5:7]) / 2

    # Plot bar
    ax.bar(range(7), week_bins)

    # Plot averages
    ax.text(
        2,
        weekday_avg * 1.05,
        f"Gjennomsnitt ukedager: {weekday_avg * 100:.0f}{percent()}",
    )
    ax.text(
        4.5,
        weekend_avg * 1.1,
        f"Gjennomsnitt helgedager: {weekend_avg * 100:.0f}{percent()}",
    )
    ax.plot((0, 5 - 1), (weekday_avg, weekday_avg), "k--")
    ax.plot((5, 7 - 1), (weekend_avg, weekend_avg), "k--")

    # Decorate axes
    ax.set_xticklabels(
        ("", "Mandag", "Tirsdag", "Onsdag", "Torsdag", "Fredag", "Lørdag", "Søndag")
    )
    ax.set_yticklabels(
        [f"{openness * 100:.1f}{percent()}" for openness in ax.get_yticks()]
    )
    ax.set_ylabel("p", rotation=0)


def plot_openness_by_weekday_by_semester(period: dict, ax: Axes):
    """
    Plot openness by semester.

    :param period: Period over which to average the openness
    :param ax: Axes object in which to put the plot
    :return: None
    """
    # Configuration
    num_weekdays = 5
    init_year = 2015
    init_semester = "Vår"

    # Get data for plot
    dataseries = get_openness_by_weekday_by_semester(period)
    num_series = len(dataseries)
    bar_width = 1 / (num_series + 1)

    # Create plot
    cur_year = init_year
    cur_semester = init_semester
    legend = []
    for semester_index, week_bins in enumerate(dataseries):
        # Add bars
        ax.bar(
            [
                weekday_index + semester_index * bar_width
                for weekday_index in range(num_weekdays)
            ],
            height=week_bins[:num_weekdays],
            width=bar_width,
        )

        # Add to legend
        legend.append(f"{cur_semester} {cur_year}")

        # Update semester and year for next bars
        if cur_semester == "Høst":
            cur_semester = "Vår"
            cur_year += 1
        else:
            cur_semester = "Høst"

    # Place legend and labels
    ax.legend(legend, loc="lower right")
    ax.set_xticklabels(("", "Mandag", "Tirsdag", "Onsdag", "Torsdag", "Fredag"))
    ax.set_yticklabels(
        [f"{openness * 100:.1f}{percent()}" for openness in ax.get_yticks()]
    )
    ax.set_ylabel("p", rotation=0)


def plot_visit_durations(data: list, ax: Axes):
    """
    Plot the visit durations from the raw data.

    :param data: Raw data
    :param ax: Axes object in which to put the plot
    :return: None
    """
    # Histogram options
    min_visit_s = 30
    max_visit_s = 60 * 60 * 3
    nbins = 150

    # Regression line options
    fit_start = 6
    fit_stop = 144

    # Create histogram
    durations = get_visit_durations(data)
    n, bins, _ = ax.hist(durations, bins=linspace(min_visit_s, max_visit_s, nbins))

    # Create regression line
    bin_width = (bins[fit_stop - 1] - bins[fit_start]) / (fit_start - fit_stop)
    lin_fitting_bins = [b + bin_width / 2 for b in bins[fit_start:fit_stop]]
    lin_fitting_n = n[fit_start:fit_stop]
    [a, b] = polyfit(lin_fitting_bins, log(lin_fitting_n), 1, w=sqrt(lin_fitting_n))
    fitted_n = [exp(b + a * t) for t in lin_fitting_bins]
    regression_line_opts = {"linestyle": "--", "color": "black", "linewidth": 2}
    regression_label_text = "y={:.0f}exp({:.6f}*t)".format(exp(b), a)
    regression_label_coords = (max_visit_s * 0.6, max(n) * 0.5)
    ax.plot(lin_fitting_bins, fitted_n, **regression_line_opts)
    ax.text(*regression_label_coords, regression_label_text)

    # Label axes
    ax.set_xlabel("Varighet for visitt (s)")
    ax.set_ylabel("Andel visitter (vilkårlig)")
    ax.set_yscale("log")


def plot_all(data: list):
    """
    Plot everything based on the raw data.

    :param data: Raw data
    :return: None
    """
    # Config
    plt.figure(figsize=(15, 8))
    grid_shape = (3, 2)
    fine_grained_sampling_period = {"minutes": 1}

    # Openness by week for the entire period
    openness_ax = plt.subplot2grid(grid_shape, (0, 0), colspan=2)
    plot_openness(data, {"days": 7}, openness_ax)

    # Openness by hour for the entire period
    openness_by_hour_ax = plt.subplot2grid(grid_shape, (1, 0))
    plot_openness_by_hour(data, fine_grained_sampling_period, openness_by_hour_ax)

    # Duration of visits
    visit_duration_ax = plt.subplot2grid(grid_shape, (1, 1))
    plot_visit_durations(data, visit_duration_ax)

    # Openness by weekday
    openness_by_weekday_ax = plt.subplot2grid(grid_shape, (2, 0))
    plot_openness_by_weekday(data, fine_grained_sampling_period, openness_by_weekday_ax)

    # Openness by weekday by semester
    openness_by_weekday_by_semester_ax = plt.subplot2grid(grid_shape, (2, 1))
    plot_openness_by_weekday_by_semester(
        fine_grained_sampling_period, openness_by_weekday_by_semester_ax
    )

    # Show the plot
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    # Get data
    data = list(get_rows())

    # Use LaTeX rendering if available
    rcParams["text.usetex"] = is_tex_available()

    # Plot
    plot_all(data)
