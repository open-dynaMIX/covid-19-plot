#!/usr/bin/env python3


import argparse
import csv
import datetime
import glob
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
CSV_DIR = f"{DIR_PATH}/COVID-19/csse_covid_19_data/csse_covid_19_time_series"
CSV_PATHS = {
    "confirmed": f"{CSV_DIR}/time_series_19-covid-Confirmed.csv",
    "deaths": f"{CSV_DIR}/time_series_19-covid-Deaths.csv",
    "recovered": f"{CSV_DIR}/time_series_19-covid-Recovered.csv",
}


def group(number):
    s = "%d" % number
    groups = []
    while s and s[-1].isdigit():
        groups.append(s[-3:])
        s = s[:-3]
    return s + "'".join(reversed(groups))


def valid_date(s):
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


def parse_arguments(args):
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "countries",
        type=str,
        nargs="*",
        default=["Switzerland"],
        help="List of countries/regions (defaults to Switzerland)",
    )
    parser.add_argument(
        "-l", "--logarithmic", action="store_true", help="use logarithmic scale"
    )
    parser.add_argument(
        "-c", "--confirmed", action="store_true", help="include confirmed (default)",
    )
    parser.add_argument("-d", "--deaths", action="store_true", help="include deaths")
    parser.add_argument(
        "-r", "--recovered", action="store_true", help="include recovered"
    )
    parser.add_argument("-a", "--all", action="store_true", help="include all")
    parser.add_argument(
        "-s",
        "--startdate",
        help="plot data past given date - format YYYY-MM-DD",
        type=valid_date,
    )
    parser.add_argument(
        "--no-annotate", help="disable annotation of data points", action="store_true",
    )
    parser.add_argument(
        "--split-by-state",
        action="store_true",
        help="show graph for each province/state",
    )
    parser.add_argument(
        "--list-countries", action="store_true", help="list available countries/regions"
    )
    args = parser.parse_args(args)

    if args.all:
        args.confirmed = args.deaths = args.recovered = True
    elif args.confirmed is args.deaths is args.recovered is False:
        args.confirmed = True

    return args


def get_data_from_file(file, countries, split_by_state, startdate):
    data = {}
    with open(file) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            area = row["Country/Region"].strip()
            if area in countries:
                state = row.pop("Province/State").strip()
                country = row.pop("Country/Region").strip()
                row.pop("Lat")
                row.pop("Long")
                x = []
                y = []
                for date, count in row.items():
                    # can't use strptime with non-padded month
                    month, day, year = date.split("/")
                    date = datetime.date(int(f"20{year}"), int(month), int(day))
                    if startdate and date < startdate:
                        continue
                    x.append(date)
                    y.append(int(count))
                if split_by_state:
                    area = f"{country} - {state}"
                if area not in data:
                    data[area] = {}
                if not data[area] or split_by_state:
                    data[area] = {"x": x, "y": y}
                    continue
                for ct, i in enumerate(y):
                    data[area]["y"][ct] += i
    return data


def get_data(countries, args):
    """
    Collects data from CSVs

    `data` has following structure:

    {
        "Switzerland": {
            "confirmed": [],
            "deaths": [],
            "recovered": []
        },
        ...
    }

    """

    def add_to_data(sdata, key):
        for area, d in sdata.items():
            if area not in data:
                data[area] = {}
            data[area][key] = sdata[area]

    data = {}

    if args.confirmed:
        sub_data = get_data_from_file(
            CSV_PATHS["confirmed"], countries, args.split_by_state, args.startdate
        )
        add_to_data(sub_data, "confirmed")

    if args.deaths:
        sub_data = get_data_from_file(
            CSV_PATHS["deaths"], countries, args.split_by_state, args.startdate
        )
        add_to_data(sub_data, "deaths")

    if args.recovered:
        sub_data = get_data_from_file(
            CSV_PATHS["recovered"], countries, args.split_by_state, args.startdate
        )
        add_to_data(sub_data, "recovered")

    return data


def get_countries():
    os.chdir(f"{DIR_PATH}/COVID-19/csse_covid_19_data/csse_covid_19_daily_reports")

    regions = []
    for file in sorted(glob.glob("*.csv")):
        with open(file) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                regions.append(row["Country/Region"].strip())
    return sorted(set(regions))


def setup_plot(args):
    plt.gcf().subplots_adjust(bottom=0.15)
    font = {
        "family": "sans-serif",
        "color": "black",
        "weight": "normal",
        "size": 21,
    }

    plt.title("Linear", fontdict=font)
    if args.logarithmic:
        plt.yscale("log")
        plt.title("Logarithmic", fontdict=font)

    plt.xlabel("Days", fontdict=font)
    plt.ylabel("Cases", fontdict=font)


def plot(data, args):
    def y_ticks():
        yticks = plt.yticks()
        new_diff = (yticks[0][1] - yticks[0][0]) / 4
        if not args.logarithmic:
            ticks = np.arange(0, yticks[0][-1], step=new_diff)
            labels = [
                group(tick) for tick in np.arange(0, yticks[0][-1], step=new_diff)
            ]
            plt.yticks(ticks, labels=labels)

    setup_plot(args)

    first_key = next(iter(data))
    second_key = next(iter(data[first_key]))
    x = data[first_key][second_key]["x"]
    plt.xticks(x, labels=[date.strftime("%Y-%m-%d") for date in x], rotation=70)

    legend = []
    plots = []
    linestyle = {"confirmed": "solid", "deaths": "dashed", "recovered": "dotted"}
    for area, area_data in data.items():
        color = None
        for category, data in area_data.items():
            plots.append(
                plt.plot(
                    data["x"],
                    data["y"],
                    color=color,
                    linestyle=linestyle[category],
                    marker=".",
                )
            )
            if not args.no_annotate:
                for ct, i in enumerate(data["y"]):
                    plt.annotate(
                        group(i),
                        (data["x"][ct], i),
                        bbox=dict(facecolor="white", alpha=0.30),
                    )
            color = plots[-1][0].get_color()
            legend.append(f"{area} - {category}")

    y_ticks()

    plt.grid()
    plt.legend(legend)
    return plots


def main():
    args = parse_arguments(sys.argv[1:])

    if args.list_countries:
        print("\n".join(get_countries()))
        sys.exit(0)

    data = get_data(args.countries, args)

    plot(data, args)
    try:
        plt.show()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":  # pragma: no cover
    main()
