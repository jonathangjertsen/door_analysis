"""
This module does door statistics.
"""
from csv import reader
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from functools import lru_cache
from os.path import dirname, realpath
from types import GeneratorType

# Index of the status and timestamp elements in a data row
STATUS = 0
TS = 1

# Value of a status when it is closed or open
CLOSED = 0
OPEN = 1

# CSV file location and data format
DOOR_CSV_PATH = dirname(realpath(__file__)) + "/door.csv"
DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


def limit_filter_func(start, stop):
    """
    Returns a function which filters the data by date.
    """
    return lambda _, timestamp: start < timestamp < stop


@lru_cache()
def get_all_rows() -> list:
    """
    Returns all rows as a list of (status, datetime) tuples
    """
    with open(DOOR_CSV_PATH, "r") as file:
        csv_reader = reader(file, delimiter=",")
        return [
            (int(row[STATUS]), datetime.strptime(row[TS], DATETIME_FMT))
            for row in csv_reader
        ]


def get_rows(filter_func: callable = None) -> GeneratorType:
    """
    Reads door.csv and returns a generator which yields the data one by one.

    Call list(get_rows()) to get the whole thing as a list.
    """
    for status, timestamp in get_all_rows():
        if filter_func is None or filter_func(status, timestamp):
            yield status, timestamp


def get_openness(data: list, period: dict) -> (list, list):
    """
    Extracts the openness from the raw data.

    :param data: Raw data
    :param period: Period over which to average the openness
    :return: datetimes (x-axis) and opennesses (y-axis)
    """
    # Init state
    min_date = data[0][TS]
    max_date = data[-1][TS]

    openness = []
    datetimes = []

    # And now for the tricky bit!
    # We take regular samples, but the data points will be irregularly spaced, so
    # there may be zero, one or many samples between each data point.
    # This algorithm uses 4 "cursors": one for the current and previous sampling point,
    # and one for the current and previous data point.

    # Initialize the cursors
    prev_idx = 0
    cur_idx = 1
    prev_data = data[prev_idx][TS]
    cur_data = data[cur_idx][TS]
    prev_sample = min_date
    cur_sample = min_date + timedelta(**period)

    # Iterate through the sampling period
    while cur_sample <= max_date:
        # If the current datapoint is beyond the current date, we assign a 1.0 or a
        # 0.0 to the current sample (the door was closed or open for the full period)
        if cur_data > cur_sample:
            if data[prev_idx][STATUS] == OPEN:
                cur_openness = 1.0
            else:
                cur_openness = 0.0
        # Otherwise, there is one or more sample within the current sample period.
        else:
            # Initialize the openness at 0
            cur_openness = 0.0

            # Iterate through every row until we reach the current sample
            while cur_data <= cur_sample:
                # Add openness proportional to the time that the door was open
                if data[prev_idx][STATUS] == OPEN:
                    cur_openness += (cur_data - prev_data) / (cur_sample - prev_sample)

                # Increment data indices
                prev_idx = cur_idx
                cur_idx += 1
                if cur_idx >= len(data):
                    break

                # Increment data cursors
                prev_data = data[prev_idx][TS]
                cur_data = data[cur_idx][TS]

            # This would need to be explained with a drawing
            if data[prev_idx][STATUS] == OPEN:
                cur_openness += (cur_sample - prev_data) / (cur_sample - prev_sample)

        # Snap prev_data cursor to the sampling grid
        prev_data = cur_sample

        # Add data for this sampling point
        openness.append(cur_openness)
        datetimes.append(cur_sample)

        # Increment sample cursors
        prev_sample = cur_sample
        cur_sample += timedelta(**period)

    return datetimes, openness


def get_openness_by_hour(data: list, period: dict) -> list:
    """
    Extracts the openness by hour from the raw data.

    :param data: Raw data
    :param period: Period over which to average the openness
    :return: A list with 25 entries (bins[7] is for 07:00, bins[15] for 15:00, and so on)
    """
    # Init bins
    hour_bins = [0] * (24 + 1)
    num_samples_by_hour = [0] * (24 + 1)

    # Get opennesses for each weekday
    for dt, openness in zip(*get_openness(data, period)):
        h = dt.hour + 1
        hour_bins[h] += openness
        num_samples_by_hour[h] += 1

    # Normalize each week bin
    for h in range(1, 24 + 1):
        try:
            hour_bins[h] = hour_bins[h] / num_samples_by_hour[h]
        except ZeroDivisionError:
            hour_bins[h] = 0
    return hour_bins


def get_openness_by_weekday(data: list, period: dict) -> list:
    """
    Extract the openness by weekday from the raw data.

    :param data: Raw data
    :param period: Period over which to average the openness
    :return: A list with 7 entries (bins[0] is Monday, bins[3] is Thursday, and so on)
    """
    # Init state
    week_bins = [0] * 7
    num_samples_by_weekday = [0] * 7

    # Get opennesses for each weekday
    for dt, openness in zip(*get_openness(data, period)):
        weekday = dt.weekday()
        week_bins[weekday] += openness
        num_samples_by_weekday[weekday] += 1

    # Normalize each week bin
    for w in range(7):
        try:
            week_bins[w] = week_bins[w] / num_samples_by_weekday[w]
        except ZeroDivisionError:
            week_bins[w] = 0
    return week_bins


def get_openness_by_semester(period: dict):
    # Config
    stop = datetime.today()
    start = datetime(2015, 1, 1)

    # Get opennesses for each semester
    # Maybe optimize this to avoid reading the entire csv-file 6+ times
    cur_start = start
    cur_stop = cur_start + relativedelta(months=6)
    semesters = []
    while cur_start < stop:
        # Get openness for the semester
        rows = list(get_rows(limit_filter_func(cur_start, cur_stop)))
        if rows:
            semesters.append(get_openness(rows, period))

        # Update start and stop to next semester
        cur_start = cur_stop
        cur_stop += relativedelta(months=6)
    return semesters


def get_openness_by_weekday_by_semester(period: dict) -> list:
    """
    Get raw data and extract the openness by semester.

    :param period: Period over which to average the openness
    :return: A list of data organized by semester
    """
    # Get openness by semester
    semesters = get_openness_by_semester(period)

    # Place opennesses in bins by weekday
    dataseries = []
    for datetimes, opennesses in semesters:
        week_bins = [0] * 7
        num_samples_by_weekday = [0] * 7

        # Get opennesses for each weekday
        for dt, openness in zip(datetimes, opennesses):
            weekday = dt.weekday()
            week_bins[weekday] += openness
            num_samples_by_weekday[weekday] += 1

        # Normalize each week bin
        for i in range(7):
            try:
                week_bins[i] = week_bins[i] / num_samples_by_weekday[i]
            except ZeroDivisionError:
                week_bins[i] = 0
        dataseries.append(week_bins)
    return dataseries


def get_visit_durations(data: list) -> list:
    """
    Extract the visit durations from the raw data.

    :param data: Raw data
    :return: A list of the durations for every visit
    """
    # Set init status
    prev_timestamp = data[0][TS]
    prev_status = CLOSED
    visit_start = prev_timestamp

    # Find visit durations
    durations = []
    for [status, timestamp] in data[1:]:
        if status == OPEN and prev_status == CLOSED:
            visit_start = timestamp
        elif status == CLOSED and prev_status == OPEN:
            durations.append((timestamp - visit_start).total_seconds())
        prev_status = status

    return durations
