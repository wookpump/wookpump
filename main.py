import time
from bittrex import Bittrex
import json
from decimal import *
import sys

def buyCoin(coinName, rate):
    coinName = 'BTC-'+coinName
    print(rate)
    askPrice = float('%.8f' % bittrex.get_ticker(coinName)['result']['Ask']) * rate
    askPrice = '%.8f' % float(askPrice)
    qty = round(float(0.1 / float(askPrice)), 8)
    buyResult = bittrex.buy_limit(coinName, qty, askPrice)['result']
    myOrderHistory = bittrex.get_order_history(coinName, 1)
    openOrders = bittrex.get_open_orders(coinName)
    return askPrice, buyResult, myOrderHistory, openOrders

def sellCoin(coinName,bidPrice, rate):
    coinAvail = '%.10f' % float(bittrex.get_balance(coinName)['result']['Available'])
    #bidPrice = float('%.8f' % bittrex.get_ticker('BTC-'+coinName)['result']['Bid']) * rate
    bidPrice = '%.8f' % (float(bidPrice) * rate)
    print(bidPrice)
    buyResult = bittrex.sell_limit('BTC-' + coinName, coinAvail, bidPrice)['result']
    myOrderHistory = bittrex.get_order_history(coinName, 1)
    openOrders = bittrex.get_open_orders(coinName)
    return buyResult, myOrderHistory, openOrders

with open("secrets.json") as secrets_file:
    secrets = json.load(secrets_file)
    secrets_file.close()
    bittrex = Bittrex(secrets['key'], secrets['secret'])

coinName = sys.argv[1].upper()
print(coinName)
askPrice, buyResult, myOrderHistory, openOrders = buyCoin(coinName,1.2)
print(str(buyResult))

sellResult, myOrderHistory, openOrders = sellCoin(coinName,askPrice, 2.5)
print(str(sellResult))

#print(str(myOrderHistory))
#print(str(openOrders))
