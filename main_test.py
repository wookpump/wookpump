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
                ticker = bittrex.get_ticker(self.MarketName)
                price = float('%.10f' % ticker['result']['Ask'])
                dict_priv = dict_price[self.MarketName][1]
                dict_curr = {current_time:price}
                dict_price.update({self.MarketName:[dict_priv,dict_curr]})
                print(self.MarketName + ' : ' + str(price))
            except:
                # print(self.MarketName + ' : error')
                traceback.print_exc()
            
            time.sleep(2.1)

def buyCoin(coinName, rate):
    coinName = 'BTC-'+coinName
    print(rate)
    askPrice = float('%.8f' % bittrex.get_ticker(coinName)['result']['Ask']) * rate
    askPrice = '%.8f' % float(askPrice)
    qty = round(float(0.3 / float(askPrice)), 8)
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

#coinName = sys.argv[1].upper()
#print(coinName)
#askPrice, buyResult, myOrderHistory, openOrders = buyCoin(coinName,1.2)
#print(str(buyResult))

#sellResult, myOrderHistory, openOrders = sellCoin(coinName,askPrice, 2.5)
#print(str(sellResult))
result = bittrex.get_markets()
print(result)
for coin in result['result']:
    MarketName = coin['MarketName']
    if 'BTC-' in MarketName:
        try:
            #ticker = bittrex.get_ticker(MarketName)
            #currency =  float('%.8f' % ticker['result']['Ask'])
            #print(ticker)
            #print(MarketName + ' : ' + str(currency))
            dict_price.update({MarketName:[{},{}]})
            ThreadGetTiker(MarketName).start()
        except:
            print('error : ' + MarketName)
            #print(MarketName + ' : ' + str(currency))
while True:
    print(dict_price)
    time.sleep(5)
#print(result)
#print(str(myOrderHistory))
#print(str(openOrders))
