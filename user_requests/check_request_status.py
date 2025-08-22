import argparse
from UserRequestHandler import UserRequestHandler

import os
os.environ["DB_USER"] = 'dataEngDB'
os.environ["DB_PASS"] = 'dataEngDB'
# os.environ["DB_USER"] = 'zms14'
# os.environ["DB_PASS"] = 'DataEng2025'
os.environ["DB_NAME"] = 'Inventory'


def collect_inputs():
    parser = argparse.ArgumentParser(description="Fetch Landsat data from"
                                     "inventory or create request for"
                                     "unavailable data")
    parser.add_argument("-r", "--request_id", type=str, help="ID for"
                        "landsat download request", required=True)
    return parser.parse_args()


def parse_inputs(args_dict):
    request_id = validate_request_id(args_dict.request_id)
    return request_id


def validate_request_id(request_id):
    if not request_id:
        raise ValueError("Request ID cannot be empty")

    if not isinstance(request_id, str):
        raise ValueError("Request ID must be a string")

    return request_id


def check_request_status(request_id):
    request_status = UserRequestHandler.get_request_status(request_id)
    if request_status is None:
        print(f"Request ID {request_id} not found. Please check the ID and "
              "try again.")
    else:
        print(f"Request ID {request_id} status: {request_status}")


def main():
    args = collect_inputs()
    request_id = parse_inputs(args)
    check_request_status(request_id)


if __name__ == "__main__":
    main()
