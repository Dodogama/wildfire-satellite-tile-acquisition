""" Class to handle user requests for Landsat tile data."""

import os
from datetime import datetime
import json
import uuid
import numpy as np
from pystac_client import Client
from google.cloud.sql.connector import Connector
import sqlalchemy
from wrs_conv.get_wrs import ConvertToWRS


class UserRequestHandler():

    def __init__(self, nw_coord, se_coord, start_date, end_date,
                 output_dir="./data"):
        self.nw_coord = nw_coord
        self.se_coord = se_coord
        self.start_date = start_date
        self.end_date = end_date
        self.output_dir = output_dir

        self.stac_query_base = {
            'landsat:collection_number': {'in': ['02']},
            'landsat:collection_category': {'in': ['T1']},
            'platform': {'in': ['LANDSAT_8']},
            'card4l:specification': {'in': ['SR']},
            }

        self.conv = self.setup()

    def setup(self):
        # validate inputs
        UserRequestHandler.validate_coordinates(self.nw_coord)
        UserRequestHandler.validate_coordinates(self.se_coord)
        UserRequestHandler.validate_date(self.start_date)
        UserRequestHandler.validate_date(self.end_date)

        db_user, db_pass, db_name = UserRequestHandler.get_db_credentials()
        self.db_user = db_user
        self.db_pass = db_pass
        self.db_name = db_name

        # create directory for output data if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # create instance of ConvertToWRS class
        conv = ConvertToWRS()
        return conv

    def make_landsat_request(self):
        # get all requested tile IDs from the user
        requested_tile_ids = self.get_requested_tileIDs()

        # query the database for cached tiles
        cached_tiles = self.query_cached_tiles(self.wrs_tiles)

        # determine which tiles need to be downloaded
        download_tiles = self.determine_download_tiles(cached_tiles,
                                                       requested_tile_ids)

        # save cached tiles to the output directory if they exist
        is_cache_data = False
        if cached_tiles:
            cached_filename = os.path.join(self.output_dir,
                                           f'tile_request_{self.nw_coord[0]}_'
                                           f'{self.nw_coord[1]}_'
                                           f'{self.se_coord[0]}_'
                                           f'{self.se_coord[1]}_'
                                           f'{self.start_date}_'
                                           f'{self.end_date}.json')
            with open(cached_filename, 'w') as f:
                json.dump(cached_tiles, f, indent=4)
            is_cache_data = True

        # make the download request in the postgres database if needed
        is_download_data = False
        if download_tiles:
            self.make_download_request(download_tiles)
            is_download_data = True

        # print information to user based on cache data and download data
        if is_cache_data and is_download_data:
            print("Some tiles were available in the cache. These files are "
                  f"are available in {cached_filename}.")
            print("A request to download the remaining tiles has been made. "
                  f"Your request ID is: {self.request_id}.")
        elif is_cache_data:
            print("All requested tiles were available in the cache. These "
                  f"files are available in {cached_filename}.")
        elif is_download_data:
            print("No tiles were available in the cache. A request to download"
                  " all requested tiles has been made. Your request ID is: "
                  f"{self.request_id}.")
        else:
            print("No tiles were found matching your request. Please check the"
                  " coordinates and date range and try again.")

    def get_requested_tileIDs(self):
        # call tile and timeframe acquisition functions to get IDs/names for
        # all of the tiles requested by the user
        self.wrs_tiles = self.get_wrs_tiles()
        requested_tiles = self.get_spatiotemporal_tiles(self.wrs_tiles)
        return requested_tiles

    def make_download_request(self, download_tiles):
        connector, pool = self.connect_to_postgres()

        request_id = self.make_request_id()
        request_status = "Queued"

        # get list of file IDs currently in the RequestFiles table
        with pool.connect() as db_conn:
            result = db_conn.execute(
                sqlalchemy.text("SELECT fileID FROM Inventory.RequestFiles;")
            ).fetchall()
            if result:
                ids_in_rf = [row[0] for row in result]
            else:
                ids_in_rf = []
        ids_in_rf = set(ids_in_rf)

        # remove any file IDs that are already in the RequestFiles table
        download_tiles = list(set(download_tiles) - ids_in_rf)

        # insert into Requests table
        insert_request_query = """
            INSERT INTO Inventory.Requests
            (requestID, status, requestTime)
            VALUES (:request_id, :request_status, :request_time);
        """

        # prepare data for RequestFiles table
        insert_files_query = """
            INSERT INTO Inventory.RequestFiles
            (fileID, requestID, processed, downloaded)
            VALUES (:file_id, :request_id, :processed, :downloaded);
        """
        request_files_data = [
            {"file_id": file_id,
             "processed": "FALSE",
             "downloaded": None,
             "request_id": request_id} for file_id in download_tiles]

        with pool.connect() as db_conn:
            try:
                # make a single insert into Requests table
                db_conn.execute(sqlalchemy.text(insert_request_query), {
                    "request_id": request_id,
                    "request_status": request_status,
                    "request_time": datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                        )
                })

                # db_conn.commit()

                # batch insert into RequestFiles table
                db_conn.execute(sqlalchemy.text(insert_files_query),
                                request_files_data)

                db_conn.commit()
                self.request_id = request_id  # Save the request ID user
            except Exception as e:
                db_conn.rollback()  # rollback to prevent partial transaction
                raise e

        # connector.close()

    def make_request_id(self):
        return str(uuid.uuid4())

    def query_cached_tiles(self, wrs_tiles):
        connector, pool = self.connect_to_postgres()

        # query the database for cached tiles
        cached_tiles = []
        with pool.connect() as db_conn:
            for tile in wrs_tiles:
                # get all cached tiles for the given path/row
                path = UserRequestHandler.pad_to_n_digits(str(tile[0]), 3)
                row = UserRequestHandler.pad_to_n_digits(str(tile[1]), 3)

                tile_stmt = """
                    SELECT * FROM inventory.tiles WHERE wrspath=:path AND
                    wrsrow=:row;
                """
                result = db_conn.execute(
                    sqlalchemy.text(tile_stmt),
                    {"path": path, "row": row}).fetchall()

                # saved all cached tile fields
                result_dict = [{
                    "fileID": row[0],
                    "bucketLink": row[1],
                    "wrsRow": row[3],
                    "wrsPath": row[4],
                    "date": row[2].strftime("%Y-%m-%d %H:%M:%S")
                    } for row in result]
                cached_tiles.extend(result_dict)
        # connector.close()
        return cached_tiles

    def determine_download_tiles(self, cached_tiles, requested_tile_ids):
        connector, pool = self.connect_to_postgres()

        cached_tile_ids = set()
        for tile in cached_tiles:
            # get the tile ID from the cached tile
            tile_id = tile['fileID']
            cached_tile_ids.add(tile_id)

        download_tiles = list(set(requested_tile_ids) - cached_tile_ids)
        return download_tiles

    def connect_to_postgres(self):
        db_user = self.db_user
        db_pass = self.db_pass
        db_name = self.db_name

        connector, pool = UserRequestHandler.create_postgres_conn(
                                                db_user, db_pass, db_name)
        return connector, pool

    def convert_to_wrs(self):
        # convert coordinates to WRS-2 path/row
        nw_wrs = self.conv.get_wrs(self.nw_coord[0], self.nw_coord[1])
        se_wrs = self.conv.get_wrs(self.se_coord[0], self.se_coord[1])

        return nw_wrs, se_wrs

    def get_wrs_tiles(self):
        # get WRS-2 tiles for the given coordinates
        nw_wrs, se_wrs = self.convert_to_wrs()

        # separate paths and rows for NW and SE corners
        nw_path = nw_wrs[0]['path']
        nw_row = nw_wrs[0]['row']
        se_path = se_wrs[0]['path']
        se_row = se_wrs[0]['row']

        # since users request a rectangle define by the NW and SE corners, we
        # need to create a grid of all the paths and rows in between the
        # corners. min and max to account of ordering mismatch
        paths = np.array(range(min(nw_path, se_path),
                               max(nw_path, se_path) + 1))
        rows = np.array(range(min(nw_row, se_row),
                              max(nw_row, se_row) + 1))

        wrs_tiles = np.meshgrid(paths, rows)
        wrs_tiles = np.array(wrs_tiles).T.reshape(-1, 2)

        return wrs_tiles

    def get_spatiotemporal_tiles(self, tile_list):
        # create connection to landsat tile catalog (STAC)
        landsat_stac = Client.open('https://landsatlook.usgs.gov/stac-server')

        # just saving all landsat tiles requested as a list to remove from
        # once we find what tiles are currently available
        st_tiles = []
        for tile in tile_list:
            path = UserRequestHandler.pad_to_n_digits(str(tile[0]), 3)
            row = UserRequestHandler.pad_to_n_digits(str(tile[1]), 3)

            # create a query for the tile
            tile_query = {
                'landsat:wrs_row': {'in': [row]},
                'landsat:wrs_path': {'in': [path]},
                }
            total_query = {**self.stac_query_base, **tile_query}
            date_range = f"{self.start_date}/{self.end_date}"

            # execute query to STAC
            tile_search = landsat_stac.search(
                    max_items=10000,  # can change if needed, limiting for now
                    query=total_query,

                    datetime=date_range,
                    )
            # iterate over query results and save all tile names
            for item in tile_search.item_collection_as_dict()['features']:
                # check if the item is already in the list
                if item['id'] not in st_tiles:
                    # save landsat filename to list
                    st_tiles.append(item['id'])
                    # st_tiles.append({'id': item['id'],
                    #                  'row': row,
                    #                  'path': path
                    #                  })

        return st_tiles

    @staticmethod
    def validate_coordinates(coord):
        if len(coord) != 2:
            raise ValueError("Coordinates must be a tuple of (latitude,"
                             "longitude)")
        lat, lon = coord
        if not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise ValueError("Latitude must be between -90 and 90, and"
                             "longitude must be between -180 and 180")
        return True

    @staticmethod
    def validate_date(date_str):
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Invalid date provided. Dates must be in"
                             " YYYY-MM-DD format and contain a valid date.")

    @staticmethod
    def pad_to_n_digits(num_str, n):
        # pad the number with leading zeros to make it 3 digits
        return num_str.zfill(n)

    @staticmethod
    def get_db_credentials():
        # get database credentials from environment variables
        db_user = os.environ.get("DB_USER")
        db_pass = os.environ.get("DB_PASS")
        db_name = os.environ.get("DB_NAME")

        if not db_user or not db_pass or not db_name:
            raise ValueError("Database credentials must be set as environment"
                             " variables called 'DB_USER', 'DB_PASS', and"
                             "'DB_NAME'")
        return db_user, db_pass, db_name

    @staticmethod
    def create_postgres_conn(db_user, db_pass, db_name):
        connector = Connector()

        def getconn():
            conn = connector.connect(
                # "ece590-de-451315:us-central1:de-postgres",
                "gentle-shell-451314-m0:us-central1:de-postgre",
                "pg8000",
                user=db_user,
                password=db_pass,
                db=db_name,
            )
            return conn

        pool = sqlalchemy.create_engine(
                    "postgresql+pg8000://",
                    creator=getconn,
                )
        return connector, pool

    @staticmethod
    def get_request_status(request_id):
        db_user, db_pass, db_name = UserRequestHandler.get_db_credentials()
        connector, pool = UserRequestHandler.create_postgres_conn(
                                                db_user, db_pass, db_name)

        # query the database for the request status
        with pool.connect() as db_conn:
            # request_stmt = """
            #     SELECT status FROM Inventory.Requests WHERE
            #     requestID=:request_id;
            # """
            # result = db_conn.execute(
            #     sqlalchemy.text(request_stmt),
            #     {"request_id": request_id}).fetchone()

            # if result:
            #     status = result[0]
            # else:
            #     status = None

            request_stmt = """
                SELECT processed FROM Inventory.RequestFiles WHERE
                requestID=:request_id;
            """
            result = db_conn.execute(
                sqlalchemy.text(request_stmt),
                {"request_id": request_id}).fetchall()

            if result:
                n_tiles = len(result)
                n_processed = sum([1 for row in result if row[0]])
                if n_tiles == n_processed:
                    status = "Completed."
                elif n_processed == 0:
                    status = "Queued."
                else:
                    progress = (n_processed / n_tiles) * 100
                    status = f"In Progress - {round(progress, 1)}% completed."
            else:
                status = None
        # connector.close()
        return status
