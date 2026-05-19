import talib.abstract as ta
import pandas as pd

df = pd.read_feather('user_data/data/coinbase/BTC_USDT-5m.feather')
df['ema9'] = ta.EMA(df, timeperiod=9)
df['ema21'] = ta.EMA(df, timeperiod=21)
df['rsi'] = ta.RSI(df, timeperiod=14)

entry_signals = ((df['ema9'] > df['ema21']) & (df['ema9'].shift(1) <= df['ema21'].shift(1)) &
                 (df['rsi'] > 45) & (df['rsi'] < 75))
exit_signals = ((df['ema9'] < df['ema21']) & (df['ema9'].shift(1) >= df['ema21'].shift(1)))

print('BTC/USDT entry signals:', entry_signals.sum())
print('BTC/USDT exit signals:', exit_signals.sum())
print('Entry dates:', df.loc[entry_signals, 'date'].head(5).to_list())
print('Exit dates:', df.loc[exit_signals, 'date'].head(5).to_list())
