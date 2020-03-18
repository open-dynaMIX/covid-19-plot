#!/usr/bin/env python3


import argparse
import csv
import datetime
import glob
import os
import sys
from bisect import bisect_left

import matplotlib.pyplot as plt
import numpy as np

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
CSV_DIR = f"{DIR_PATH}/COVID-19/csse_covid_19_data/csse_covid_19_time_series"
CSV_PATHS = {
    "confirmed": f"{CSV_DIR}/time_series_19-covid-Confirmed.csv",
    "deaths": f"{CSV_DIR}/time_series_19-covid-Deaths.csv",
    "recovered": f"{CSV_DIR}/time_series_19-covid-Recovered.csv",
}
COMPARE_CONSTANT = 100


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
        "-m",
        "--compare",
        help=f"match x-axis of multiple countries (matches the data points closest to 100 cases",
        action="store_true",
    )
    parser.add_argument(
        "--annotate", help="add annotation to data points", action="store_true",
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

    if args.compare and not args.confirmed:
        raise parser.error("Comparison is only supported based on confirmed cases.")

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
                    if state:
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
            "recovered": [],
            "shift": 0,
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


def get_shifts(data):
    shifts = {}
    max_cases = {"cases": 0, "area": None}
    for area, area_data in data.items():
        new_max = max(area_data["confirmed"]["y"])
        if new_max > max_cases["cases"]:
            max_cases["cases"] = new_max
            max_cases["area"] = area

    main_shift = 0
    if max_cases["cases"] >= COMPARE_CONSTANT:
        main_shift = bisect_left(
            data[max_cases["area"]]["confirmed"]["y"], COMPARE_CONSTANT
        )
    for area in data:
        if area == max_cases["area"]:
            shifts[area] = 0
            continue

        area_shift = 0
        if max(data[area]["confirmed"]["y"]) >= COMPARE_CONSTANT:
            area_shift = bisect_left(data[area]["confirmed"]["y"], COMPARE_CONSTANT)

        shift_diff = area_shift - main_shift
        shifts[area] = shift_diff

    return shifts


def prepare_data(data, args):
    meta = {}

    first_key = next(iter(data))
    second_key = next(iter(data[first_key]))

    meta["xticks"] = [i for i in range(len(data[first_key][second_key]["x"]))]
    meta["xticks_labels"] = [f"d{i}" for i in meta["xticks"]]
    if not args.compare:
        meta["xticks"] = data[first_key][second_key]["x"]
        meta["xticks_labels"] = [date.strftime("%Y-%m-%d") for date in meta["xticks"]]

    if args.compare:
        shifts = get_shifts(data)
        for area, area_data in data.items():
            for category, area_category_data in area_data.items():
                x_axis = [i for i in range(len(area_category_data["x"]))]
                orig_len = len(area_category_data["x"])
                if shifts[area] > 0:
                    data[area][category]["x"] = x_axis[: orig_len - shifts[area]]
                    data[area][category]["y"] = area_category_data["y"][shifts[area] :]
                elif shifts[area] < 0:
                    data[area][category]["x"] = x_axis[shifts[area] :]
                    data[area][category]["y"] = area_category_data["y"][
                        : orig_len - shifts[area]
                    ]
                elif shifts[area] == 0:
                    data[area][category]["x"] = x_axis

    return data, meta


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


def plot(data, meta, args):
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

    plt.xticks(meta["xticks"], labels=meta["xticks_labels"], rotation=70)

    legend = []
    plots = []
    linestyle = {"confirmed": "solid", "deaths": "dashed", "recovered": "dotted"}

    for area, area_data in data.items():
        color = None
        for category, area_category_data in area_data.items():
            if category == "shift":
                continue

            plots.append(
                plt.plot(
                    area_category_data["x"],
                    area_category_data["y"],
                    color=color,
                    linestyle=linestyle[category],
                    marker=".",
                )
            )
            if args.annotate:
                for ct, i in enumerate(area_category_data["y"]):
                    plt.annotate(
                        group(i),
                        (area_category_data["x"][ct], i),
                        bbox=dict(facecolor="white", alpha=0.30),
                    )
            color = plots[-1][0].get_color()
            legend.append(f"{area} - {category}")

    y_ticks()

    plt.grid()
    plt.legend(legend, loc="upper left")
    return plots


def main():
    args = parse_arguments(sys.argv[1:])

    if args.list_countries:
        print("\n".join(get_countries()))
        sys.exit(0)

    data = get_data(args.countries, args)

    data, meta = prepare_data(data, args)

    plot(data, meta, args)
    try:
        plt.show()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":  # pragma: no cover
    main()
