import talib.abstract as ta
import pandas as pd

df = pd.read_feather('user_data/data/coinbase/BTC_USDT-5m.feather')
df['rsi'] = ta.RSI(df, timeperiod=14)
macd = ta.MACD(df, fastperiod=12, slowperiod=26, signalperiod=9)
df['macd'] = macd['macd']
df['macdsignal'] = macd['macdsignal']

entry_signals = ((df['rsi'] < 30) & (df['macd'] > df['macdsignal']) & (df['macd'].shift(1) <= df['macdsignal'].shift(1)))
exit_signals = ((df['rsi'] > 70) & (df['macd'] < df['macdsignal']) & (df['macd'].shift(1) >= df['macdsignal'].shift(1)))

print('BTC/USDT entry signals (RSI<30 + MACD cross up):', entry_signals.sum())
print('BTC/USDT exit signals (RSI>70 + MACD cross down):', exit_signals.sum())
print('Sample entry dates:', df.loc[entry_signals, 'date'].head(5).to_list())
print('Sample exit dates:', df.loc[exit_signals, 'date'].head(5).to_list())
