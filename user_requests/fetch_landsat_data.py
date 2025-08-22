import argparse
from UserRequestHandler import UserRequestHandler

import os
os.environ["DB_USER"] = 'dataEngDB'
os.environ["DB_PASS"] = 'dataEngDB'
os.environ["DB_NAME"] = 'Inventory'


def collect_inputs():
    parser = argparse.ArgumentParser(description="Fetch Landsat data from"
                                     "inventory or create request for"
                                     "unavailable data")
    parser.add_argument("-nw", "--nw_coord", type=str, help="Northwest corner"
                        "coordinates (lat, lon)", required=True)
    parser.add_argument("-se", "--se_coord", type=str, help="Southeast corner"
                        "coordinates (lat, lon)", required=True)
    parser.add_argument("-sd", "--start_date", type=str,
                        help="Start date in YYYY-MM-DD format",
                        required=True)
    parser.add_argument("-ed", "--end_date", type=str,
                        help="End date in YYYY-MM-DD format",
                        required=True)
    parser.add_argument("-o", "--output_dir", type=str, help="Output directory"
                        "to save the data", default="./data")
    return parser.parse_args()


def parse_inputs(args_dict):
    nw_coord = tuple(map(float, args_dict.nw_coord.split(',')))
    se_coord = tuple(map(float, args_dict.se_coord.split(',')))
    start_date = args_dict.start_date
    end_date = args_dict.end_date
    output_dir = args_dict.output_dir

    return nw_coord, se_coord, start_date, end_date, output_dir


def main():
    args = collect_inputs()
    nw, se, sd, ed, od = parse_inputs(args)
    request_handler = UserRequestHandler(nw, se, sd, ed, od)
    request_handler.make_landsat_request()


if __name__ == "__main__":
    main()
