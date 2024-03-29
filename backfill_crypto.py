import requests
from logzero import logger
import ast
import database
from datetime import datetime 

url = "https://api.binance.com/api/v1/klines"

def fetch_data(asset, start_date):
    logger.debug(f"Fetching data on asset {asset} from {datetime.fromtimestamp(start_date/1000)}.")
    response = requests.get(url, params={'symbol': asset,
                                         'interval': "1m",
                                         'startTime': start_date,
                                         'endTime': None,
                                         'limit': 1000})
    return ast.literal_eval(response.text)

def conform_data(data):
    logger.debug("Conforming data, filling missing candles")
    output = [[data[0][0], data[0][1], data[0][2], data[0][3], data[0][4], data[0][5]]]
    for i in range(1, len(data)):
        displacement = data[i][0] - data[i - 1][0]
        if displacement != 60:
            # there is a missing candlestick here
            missing_no = (displacement - 60) / 60
            for j in range(0, int(missing_no)):
                missing_ts = data[i - 1][0] + (j + 1) * 60
                output.append([missing_ts, data[i - 1][4], data[i - 1][4], data[i - 1][4], data[i - 1][4], 0])
        output.append([data[i][0], data[i][1], data[i][2], data[i][3], data[i][4], data[i][5]])
    logger.debug(f"Data conformation successful.")
    return output

def backfill_asset(asset, start_date, reset):
    data_to_write = []
    while True:
        data = fetch_data(asset, start_date)
        if len(data) == 1:
            break
        for candle in data:
            data_to_write.append([int(candle[0] / 1000), candle[1], candle[2], candle[3], candle[4], candle[5]])
        start_date = data[-1][0]

    data_to_write = conform_data(data_to_write)
    if reset:
        database.db_create(asset)
        database.db_write(asset, data_to_write)
    else:
        database.db_write(asset, data_to_write[1:])

def get_earliest_timestamp(asset):
    response = requests.get(url, params={'symbol': asset,
                                         'interval': "1m",
                                         'startTime': 0,
                                         'endTime': None,
                                         'limit': 1})
    return ast.literal_eval(response.text)[0][0]

def backfill(asset, reset="n"):
    if reset == 'y':
        start_date = get_earliest_timestamp(asset)
        reset = True
    else:
        start_date = database.db_get_last_time(asset) * 1000
        reset = False
    backfill_asset(asset, start_date, reset)

if __name__ == "__main__":
    assets = ["BTCUSDT", "ETHUSDT"]
    for asset in assets:
        logger.debug(f"Starting backfill of {asset}")
        backfill(asset)
        logger.debug(f"Completed backfill of {asset}")