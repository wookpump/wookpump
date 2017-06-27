import time
from bittrex import Bittrex
import json
from decimal import *
import sys
import threading
from threading import Thread
import datetime
import traceback

dict_price = {}
with open("secrets.json") as secrets_file:
    secrets = json.load(secrets_file)
    secrets_file.close()
    bittrex = Bittrex(secrets['key'], secrets['secret'])


class ThreadGetTiker(Thread):
    def __init__(self, MarketName):
        self.MarketName = MarketName
        threading.Thread.__init__(self)

    def run(self):
        while True:
            try:
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ticker = bittrex.get_market_history(self.MarketName, 500)
                # print(ticker)
                list_curr = [current_time, 1]
                for i, result in enumerate(ticker['result']):
                    if i == len(ticker['result']):
                        list_curr = [current_time, result['Price']]
                # price = float('%.10f' % ticker['result']['Ask'])
                list_priv = dict_price[self.MarketName][1]
                dict_price.update({self.MarketName: [list_priv, list_curr]})
                # print(self.MarketName + ' : ' + str(price))
            except:
                # print(self.MarketName + ' : error')
                # print('')
                # continue
                traceback.print_exc()

            time.sleep(2.1)


def buyCoin(coinName, rate):
    coinName = 'BTC-' + coinName
    print(rate)
    askPrice = float('%.8f' % bittrex.get_ticker(coinName)['result']['Ask']) * rate
    askPrice = '%.8f' % float(askPrice)
    qty = round(float(0.3 / float(askPrice)), 8)
    buyResult = bittrex.buy_limit(coinName, qty, askPrice)['result']
    myOrderHistory = bittrex.get_order_history(coinName, 1)
    openOrders = bittrex.get_open_orders(coinName)
    return askPrice, buyResult, myOrderHistory, openOrders


def sellCoin(coinName, bidPrice, rate):
    coinAvail = '%.10f' % float(bittrex.get_balance(coinName)['result']['Available'])
    bidPrice = '%.8f' % (float(bidPrice) * rate)
    print(bidPrice)
    buyResult = bittrex.sell_limit('BTC-' + coinName, coinAvail, bidPrice)['result']
    myOrderHistory = bittrex.get_order_history(coinName, 1)
    openOrders = bittrex.get_open_orders(coinName)
    return buyResult, myOrderHistory, openOrders


def writeLogFile(str):
    currnet_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logfileName = currnet_time[:10].replace('-', '') + '.log'

    f = open('./logs/' + logfileName, 'a')

    f.writelines(currnet_time + ' - ' + str + '\n')
    f.close()

    # '2017-04-16 14:57:33'
    return 0


# coinName = sys.argv[1].upper()
# print(coinName)
# askPrice, buyResult, myOrderHistory, openOrders = buyCoin(coinName,1.2)
# print(str(buyResult))

# sellResult, myOrderHistory, openOrders = sellCoin(coinName,askPrice, 2.5)
# print(str(sellResult))
result = bittrex.get_markets()
# print(result)
for coin in result['result']:
    MarketName = coin['MarketName']
    if 'BTC-' in MarketName and coin['IsActive']:
        try:
            # ticker = bittrex.get_ticker(MarketName)
            # currency =  float('%.8f' % ticker['result']['Ask'])
            # print(ticker)
            # print(MarketName + ' : ' + str(currency))
            dict_price.update({MarketName: [[0, 1], [0, 1]]})
            ThreadGetTiker(MarketName).start()
        except:
            print('error : ' + MarketName)
            # print(MarketName + ' : ' + str(currency))
while True:
    # print('result -')
    for key, value in dict_price.items():
        # print(key + ' : ' + str('%.8f' % (value[0][1]-value[1][1])/value[0][1]))
        if value[0][0] != 0:
            rate = (value[1][1] - value[0][1]) / value[0][1]
            value_str = '[%s][%.8f],[%s][%.8f]' % (value[0][0], value[0][1], value[1][0], value[1][1])
            # writeLogFile(key + ' : ' + value_str + ' : ' + str('%.8f' % rate))
            if rate > 0.001:
                print(key[4:] + ' : ' + value_str + ' : ' + str('%.8f' % rate))
                writeLogFile(key + ' : ' + value_str + ' : ' + str('%.8f' % rate))
                writeLogFile('#################################### ' + key + ' #############################')
    # time.sleep(3)
# print(result)
# print(str(myOrderHistory))
# print(str(openOrders))
