import database
from logzero import logger
import pandas as pd 
import plotly.offline as py
import plotly.graph_objs as go
import numpy as np
import random
import talib
import configparser

def gen_candles(orig_raw_data, asset, start, end, candle_size):
    raw_data = orig_raw_data[:]
    start_candle = int(start + ((start / 60000) % candle_size) * 60000)
    stop_candle = int(end - ((start / 60000) % candle_size) * 60000 + candle_size * 60000)

    for i in range(0, int((start / 60000) % candle_size)):
        raw_data.pop(0)

    total_candles = int(len(raw_data) / candle_size)

    candle_data = []
    for i in range(0, total_candles):
        candle_time = raw_data[0][0]
        dic = {"open": raw_data[0][1], "high": 0, "low": 9999999999, "close": raw_data[candle_size - 1][4], "volume": 0}
        for j in range(0, candle_size):
            if raw_data[0][2] > dic["high"]:
                dic["high"] = raw_data[0][2]
            if raw_data[0][3] < dic["low"]:
                dic["low"] = raw_data[0][3]
            dic["volume"] += raw_data[0][5]
            raw_data.pop(0)
        candle_data.append([candle_time,dic])
    
    candle_data_pd = []
    for i in candle_data:
        candle_data_pd.append([i[0], i[1]["open"], i[1]["high"], i[1]["low"], i[1]["close"], i[1]["volume"]])
    df = pd.DataFrame(candle_data_pd, columns=["timestamp", "open", "high", "low", "close", "volume"])

    return df

def simple(t_start, t_end, t_back, data, sma_long_size=20, sma_short_size=5, candle_size=5):
    candles = gen_candles(data, "BTCUSDT", t_start - t_back, t_end, candle_size)
    pips_profit = 0
    flag = True
    n_trans = 0

    sma_long_v = talib.DEMA(np.array(candles.close), timeperiod=sma_long_size)
    sma_short_v = talib.DEMA(np.array(candles.close), timeperiod=sma_short_size)

    for index, row in candles.iterrows():
        if row.timestamp < t_start:
            continue

        sma_long = sma_long_v[index]
        sma_short = sma_short_v[index]

        if row.timestamp >= t_start and flag == True:
            if sma_long > sma_short:
                position = "short"
            else:
                position = "long"
            prev_close = row.close
            flag = False
            continue

        if sma_long > sma_short and position != "short":
            pips_profit += (row.close - prev_close)
            position = "short"
            prev_close = row.close
            n_trans += 1
        elif sma_long < sma_short and position != "long":
            pips_profit += (prev_close - row.close)
            position = "long"
            prev_close = row.close
            n_trans += 1

    # print(f"Pip Profit = {pips_profit} :: SMA Long = {sma_long_size}, SMA Short {sma_short_size}, Candle Size = {candle_size}")

    return [pips_profit, sma_long_size, sma_short_size, candle_size, n_trans]


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read("config.ini")
    t_start = int(config["backtest"]["StartTimestamp"])
    t_end = int(config["backtest"]["EndTimestamp"])
    t_back = 604800000 # ms in a week
    asset = "BTCUSDT"

    raw_data = database.db_slice(asset, t_start, t_end)
    
    if config["backtest"]["Algo"] == "macrossover":
        best = [0, 0, 0, 0]
        while True:
            if config["backtest"]["SampleMethod"] == "random":
                sma_long_size = random.randrange(int(config["bt_macrossover"]["SMALongRange"].split(",")[0]),
                                                 int(config["bt_macrossover"]["SMALongRange"].split(",")[1]) + 1,
                                                 int(config["bt_macrossover"]["SMALongRange"].split(",")[2]))
                sma_short_size = random.randrange(int(config["bt_macrossover"]["SMAShortRange"].split(",")[0]),
                                                 int(config["bt_macrossover"]["SMAShortRange"].split(",")[1]) + 1,
                                                 int(config["bt_macrossover"]["SMAShortRange"].split(",")[2]))
                candle_size = random.randrange(int(config["bt_macrossover"]["CandleSizeRange"].split(",")[0]),
                                               int(config["bt_macrossover"]["CandleSizeRange"].split(",")[1]) + 1,
                                               int(config["bt_macrossover"]["CandleSizeRange"].split(",")[2]))
            result = simple(t_start, t_end, t_back, raw_data, sma_long_size, sma_short_size, candle_size)
            if result[0] > best[0]:
                # we have a better result
                best = [result[0], result[1], result[2], result[3], result[4]]
                print(f"Pip Profit = {result[0]} :: SMA Long = {result[1]}, SMA Short {result[2]}, Candle Size = {result[3]}, Transactions = {result[4]}")