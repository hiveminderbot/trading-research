import pandas as pd
import talib

df = pd.read_feather('user_data/data/coinbase/BTC_USDT-5m.feather')
df['rsi'] = talib.RSI(df['close'], timeperiod=14)
bb_lower, bb_mid, bb_upper = talib.BBANDS(df['close'], timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
df['bb_lower'] = bb_lower
df['bb_upper'] = bb_upper

entry = (df['close'] <= df['bb_lower']) & (df['rsi'] < 30)
exit_s = (df['close'] >= df['bb_upper']) & (df['rsi'] > 70)

print('Entry signals (LLMStrategy):', entry.sum())
print('Exit signals (LLMStrategy):', exit_s.sum())
print('Last 5 RSI values:', df['rsi'].tail(5).tolist())
print('Last close vs BB lower:', df['close'].iloc[-1], 'vs', df['bb_lower'].iloc[-1])
print('Last close vs BB upper:', df['close'].iloc[-1], 'vs', df['bb_upper'].iloc[-1])
