import time
from bittrex import Bittrex
import json
import threading
from threading import Thread
import datetime
import traceback
from multiprocessing import Process

dict_price = {}
with open("secrets.json") as secrets_file:
    secrets = json.load(secrets_file)
    secrets_file.close()
    bittrex = Bittrex(secrets['key'], secrets['secret'])


def run(MarketName):
    while True:
        try:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ticker = bittrex.get_ticker(MarketName)
            price = float('%.10f' % ticker['result']['Ask'])
            list_priv = dict_price[MarketName][1]
            list_curr = [current_time, price]
            dict_price.update({MarketName: [list_priv, list_curr]})
        except:
            traceback.print_exc()
            print(MarketName)

        time.sleep(1)

# class ThreadGetTiker(Thread):
#     def __init__(self, MarketName):
#         self.MarketName = MarketName
#         threading.Thread.__init__(self)
#
#     def run(self):
#         while True:
#             try:
#                 current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#                 ticker = bittrex.get_ticker(self.MarketName)
#                 price = float('%.10f' % ticker['result']['Ask'])
#                 list_priv = dict_price[self.MarketName][1]
#                 list_curr = [current_time, price]
#                 dict_price.update({self.MarketName: [list_priv, list_curr]})
#             except:
#                 traceback.print_exc()
#                 print(self.MarketName)
#
#             time.sleep(1)


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
    return 0



result = bittrex.get_markets()

# for coin in result['result']:
#     MarketName = coin['MarketName']
#     if 'BTC-' in MarketName and coin['IsActive']:
#         try:
#             dict_price.update({MarketName: [[0, 1], [0, 1]]})
#             ThreadGetTiker(MarketName).start()
#         except:
#             print('error : ' + MarketName)
# while True:
#     print('result -')
#     for key, value in dict_price.items():
#         if value[0][0] != 0:
#             rate = (value[1][1] - value[0][1]) / value[0][1]
#             value_str = '[%s][%.8f],[%s][%.8f]' % (value[0][0], value[0][1], value[1][0], value[1][1])
#             writeLogFile(key + ' : ' + value_str + ' : ' + str('%.8f' % rate))
#             if rate > 0.05:
#                 print(key + ' : ' + value_str + ' : ' + str('%.8f' % rate))
#                 writeLogFile('#################################### ' + key + ' #############################')
#     time.sleep(3)

for coin in result['result']:
    MarketName = coin['MarketName']
    if 'BTC-' in MarketName and coin['IsActive']:
        try:
            dict_price.update({MarketName: [[0, 1], [0, 1]]})
            p = Process(target=run, args=(MarketName,))
            p.start()
            p.join()
        except:
            print('error : ' + MarketName)
while True:
    print('result -')
    for key, value in dict_price.items():
        if value[0][0] != 0:
            rate = (value[1][1] - value[0][1]) / value[0][1]
            value_str = '[%s][%.8f],[%s][%.8f]' % (value[0][0], value[0][1], value[1][0], value[1][1])
            writeLogFile(key + ' : ' + value_str + ' : ' + str('%.8f' % rate))
            if rate > 0.05:
                print(key + ' : ' + value_str + ' : ' + str('%.8f' % rate))
                writeLogFile('#################################### ' + key + ' #############################')
    time.sleep(3)