import pyarrow.feather as feather
import pandas as pd
import numpy as np
import talib

df = feather.read_feather('user_data/data/coinbase/BTC_USDT-5m.feather')
bb = talib.BBANDS(df['close'].values, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
rsi = talib.RSI(df['close'].values, timeperiod=14)

df['bb_lower'] = bb[2]
df['bb_upper'] = bb[1]
df['rsi'] = rsi

last = df.tail(10).copy()
last['entry_signal'] = (last['close'] <= last['bb_lower']) & (last['rsi'] < 30)
last['exit_signal'] = (last['close'] >= last['bb_upper']) & (last['rsi'] > 70)

print(last[['date','close','bb_lower','bb_upper','rsi','entry_signal','exit_signal']])
