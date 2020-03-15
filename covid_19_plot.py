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


def collect_data_from_file(file, countries):
    data_found = False
    data = {}
    with open(file) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row["Country/Region"].strip() in countries:
                confirmed, deaths, recovered = handle_row(row, data)
                if confirmed == deaths == recovered == 0:
                    continue
                data_found = True
                if row["Country/Region"] not in data:
                    data[row["Country/Region"]] = {
                        "confirmed": 0,
                        "deaths": 0,
                        "recovered": 0,
                    }
                data[row["Country/Region"]]["confirmed"] += confirmed
                data[row["Country/Region"]]["deaths"] += deaths
                data[row["Country/Region"]]["recovered"] += recovered

    return data if data_found else False


def get_data(countries):
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

    data = {
        country: {"confirmed": [], "deaths": [], "recovered": []}
        for country in countries
    }
    meta = {"dates": []}

    os.chdir(f"{DIR_PATH}/COVID-19/csse_covid_19_data/csse_covid_19_daily_reports")

    for file in sorted(glob.glob("*.csv")):
        date = datetime.strptime(file, "%m-%d-%Y.csv").date()
        sub_data = collect_data_from_file(file, countries)

        if sub_data is False and len(data[countries[0]]["confirmed"]) == 0:
            continue
        for country in countries:
            if sub_data and country in sub_data:
                data[country]["confirmed"].append(sub_data[country]["confirmed"])
                data[country]["deaths"].append(sub_data[country]["deaths"])
                data[country]["recovered"].append(sub_data[country]["recovered"])
            else:
                data[country]["confirmed"].append(
                    last_item_or_zero(data[country]["confirmed"])
                )

                data[country]["deaths"].append(
                    last_item_or_zero(data[country]["deaths"])
                )

                data[country]["recovered"].append(
                    last_item_or_zero(data[country]["recovered"])
                )
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
    for country in args.countries:
        color = None
        if args.confirmed:
            plots.append(plt.plot(x, data[country]["confirmed"]))
            color = plots[-1][0].get_color()
            legend.append(f"{country} - confirmed")

        if args.deaths:
            plots.append(
                plt.plot(
                    x,
                    data[country]["deaths"],
                    color=color if color else None,
                    linestyle="dashed",
                )
            )
            color = plots[-1][0].get_color()
            legend.append(f"{country} - deaths")

        if args.recovered:
            plots.append(
                plt.plot(
                    x,
                    data[country]["recovered"],
                    color=color if color else None,
                    linestyle="dotted",
                )
            )
            legend.append(f"{country} - recovered")

    y_ticks(args)

    plt.grid()
    plt.legend(legend)
    return plots


def main():
    args = parse_arguments(sys.argv[1:])

    if args.list_countries:
        print("\n".join(get_countries()))
        sys.exit(0)

    data, meta = get_data(args.countries)

    plot(data, meta, args)
    plt.show()


if __name__ == "__main__":  # pragma: no cover
    main()
