#!/usr/bin/env python3


import argparse
import sys
import matplotlib.pyplot as plt
import numpy as np
import csv
import glob, os
from datetime import datetime


DIR_PATH = os.path.dirname(os.path.realpath(__file__))


def group(number):
    s = "%d" % number
    groups = []
    while s and s[-1].isdigit():
        groups.append(s[-3:])
        s = s[:-3]
    return s + "'".join(reversed(groups))


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


def handle_row(row, data):
    confirmed = int(row["Confirmed"]) if row["Confirmed"] else 0
    deaths = int(row["Deaths"]) if row["Deaths"] else 0
    recovered = int(row["Recovered"]) if row["Recovered"] else 0
    return confirmed, deaths, recovered


def collect_data_from_file(file, countries, split_by_state):
    data = {}
    with open(file) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            area = row["Country/Region"].strip()
            if area in countries:
                confirmed, deaths, recovered = handle_row(row, data)
                if confirmed == deaths == recovered == 0:
                    continue
                if split_by_state:
                    state = row.get("Province/State", row.get("\ufeffProvince/State"))
                    area = f'{row["Country/Region"].strip()} - {state}'
                if area not in data:
                    data[area] = {
                        "confirmed": 0,
                        "deaths": 0,
                        "recovered": 0,
                    }
                data[area]["confirmed"] += confirmed
                data[area]["deaths"] += deaths
                data[area]["recovered"] += recovered

    return data


def get_data(countries, split_by_state):
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

    def last_item_or_zero(lst):
        if len(lst):
            return lst[-1]
        return 0

    data = {}
    meta = {"dates": []}

    os.chdir(f"{DIR_PATH}/COVID-19/csse_covid_19_data/csse_covid_19_daily_reports")

    for file in sorted(glob.glob("*.csv")):
        date = datetime.strptime(file, "%m-%d-%Y.csv").date()
        sub_data = collect_data_from_file(file, countries, split_by_state)

        if not sub_data and not data:
            continue
        for area in sub_data:
            if area not in data:
                data[area] = {
                    "confirmed": [],
                    "deaths": [],
                    "recovered": [],
                    "dates": [],
                }
            data[area]["confirmed"].append(sub_data[area]["confirmed"])
            data[area]["deaths"].append(sub_data[area]["deaths"])
            data[area]["recovered"].append(sub_data[area]["recovered"])
            data[area]["dates"].append(date)

        meta["dates"].append(date)
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
    def y_ticks(args):
        yticks = plt.yticks()
        new_diff = (yticks[0][1] - yticks[0][0]) / 4
        if not args.logarithmic:
            ticks = np.arange(0, yticks[0][-1], step=new_diff)
            labels = [
                group(tick) for tick in np.arange(0, yticks[0][-1], step=new_diff)
            ]
            plt.yticks(ticks, labels=labels)

    setup_plot(args)

    x = meta["dates"]
    plt.xticks(x, labels=[date.strftime("%Y-%m-%d") for date in x], rotation=70)

    legend = []
    plots = []
    for area, area_data in data.items():
        color = None
        if args.confirmed:
            plots.append(plt.plot(area_data["dates"], area_data["confirmed"]))
            color = plots[-1][0].get_color()
            legend.append(f"{area} - confirmed")

        if args.deaths:
            plots.append(
                plt.plot(
                    area_data["dates"],
                    area_data["deaths"],
                    color=color if color else None,
                    linestyle="dashed",
                )
            )
            color = plots[-1][0].get_color()
            legend.append(f"{area} - deaths")

        if args.recovered:
            plots.append(
                plt.plot(
                    area_data["dates"],
                    area_data["recovered"],
                    color=color if color else None,
                    linestyle="dotted",
                )
            )
            legend.append(f"{area} - recovered")

    y_ticks(args)

    plt.grid()
    plt.legend(legend)
    return plots


def main():
    args = parse_arguments(sys.argv[1:])

    if args.list_countries:
        print("\n".join(get_countries()))
        sys.exit(0)

    data, meta = get_data(args.countries, args.split_by_state)

    plot(data, meta, args)
    try:
        plt.show()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":  # pragma: no cover
    main()
