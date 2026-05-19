import pandas as pd
import pyarrow.feather as feather

# Load BTC and ETH data
btc = feather.read_feather('user_data/data/coinbase/BTC_USDT-5m.feather')
eth = feather.read_feather('user_data/data/coinbase/ETH_USDT-5m.feather')

# Calculate buy-and-hold returns
btc_start = btc['close'].iloc[0]
btc_end = btc['close'].iloc[-1]
eth_start = eth['close'].iloc[0]
eth_end = eth['close'].iloc[-1]

btc_return = (btc_end - btc_start) / btc_start * 100
eth_return = (eth_end - eth_start) / eth_start * 100
avg_return = (btc_return + eth_return) / 2

print('BTC: {:.2f} -> {:.2f} = {:+.2f}%'.format(btc_start, btc_end, btc_return))
print('ETH: {:.2f} -> {:.2f} = {:+.2f}%'.format(eth_start, eth_end, eth_return))
print('Average buy-and-hold: {:+.2f}%'.format(avg_return))

# With 1000 USDT split evenly (500 each)
btc_profit = 500 * btc_return / 100
eth_profit = 500 * eth_return / 100
total_profit = btc_profit + eth_profit
final_balance = 1000 + total_profit
print()
print('With $500 each:')
print('BTC profit: ${:.2f}'.format(btc_profit))
print('ETH profit: ${:.2f}'.format(eth_profit))
print('Total profit: ${:.2f}'.format(total_profit))
print('Final balance: ${:.2f}'.format(final_balance))
print('Total return: {:.2f}%'.format(total_profit/10))
