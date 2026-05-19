"""
Buy-and-hold benchmark strategy for Freqtrade.
Enters once at start, never exits.
"""
from freqtrade.strategy import IStrategy
from pandas import DataFrame

class BuyHoldStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '5m'
    process_only_new_candles = True
    startup_candle_count = 1
    use_exit_signal = False
    minimal_roi = {"0": 100}
    stoploss = -1.0

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe.index[0], 'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe
