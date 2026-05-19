import pyarrow.feather as feather
import talib

df = feather.read_feather('user_data/data/coinbase/BTC_USDT-5m.feather')
bb = talib.BBANDS(df['close'].values, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
rsi = talib.RSI(df['close'].values, timeperiod=14)

df['bb_lower'] = bb[2]
df['bb_upper'] = bb[1]
df['rsi'] = rsi

entry_signals = df[(df['close'] <= df['bb_lower']) & (df['rsi'] < 30)]
exit_signals = df[(df['close'] >= df['bb_upper']) & (df['rsi'] > 70)]

print('Entry signals in dataset:', len(entry_signals))
print('Exit signals in dataset:', len(exit_signals))
if len(entry_signals) > 0:
    print('Last entry:', entry_signals.iloc[-1][['date','close','bb_lower','rsi']].to_dict())
if len(exit_signals) > 0:
    print('Last exit:', exit_signals.iloc[-1][['date','close','bb_upper','rsi']].to_dict())
