import time
from bittrex import Bittrex
import json
from decimal import *
import sys
import threading
from threading import Thread
import datetime
import traceback

AUTO_TRADE = True # True or False ex)False = Display CoinName Only
BUY_COIN_UNIT = 0.01 # Total Buy bit ex)0.1 = 0.1BIT
ACCEPT_PRICE_GAP = 0.1 # Gap of prev between curr price ex)0.1 = 10%
IGNORE_GAP_SECONDS = 10 # accept time gap under 10 ex)10 = 10 second
BUY_PRICE_RATE = 1.2 # Buy coin at Current price * 1.2 ex)1.2 = 120%
SELL_PRICE_RATE = 1.03 # Sell coin at buy price(Actual) * 1.2 ex)1.2 = 120%

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
        while dict_price[self.MarketName][2]:
            try:
                current_time = datetime.datetime.now()
                current_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ticker = bittrex.get_ticker(self.MarketName)
                price = float(ticker['result']['Ask'])
                list_priv = dict_price[self.MarketName][1]
                list_curr = [current_time,price]

                #print(self.MarketName + ' : ' + str(price))

                priv_price = list_priv[1]
                curr_price = list_curr[1]

                # Check Time gap
                priv_time = dict_price[self.MarketName][0][0]
                curr_time = dict_price[self.MarketName][1][0]
                gap_seconds = (curr_time - priv_time).total_seconds()

                if gap_seconds < IGNORE_GAP_SECONDS:
                    # check price gap
                    gap_price_rate = (curr_price - priv_price) / priv_price
                    if gap_price_rate > ACCEPT_PRICE_GAP:
                        printt('#################################### ' + self.MarketName.split('-')[1] + ' #############################')
                        printt('#################################### ' + self.MarketName.split('-')[1] + ' #############################')
                        writeLogFile('#################################### ' + self.MarketName.split('-')[1] + ' #############################')
                        writeLogFile('#################################### ' + self.MarketName.split('-')[1] + ' #############################')


                        # Real Trading
                        if AUTO_TRADE :
                            # close this coin
                            dict_price.update({self.MarketName: [list_priv, list_curr, False]})
                            askPrice, buyResult, myOrderHistory, openOrders = buyCoin(self.MarketName, BUY_PRICE_RATE)
                            coinName = self.MarketName.split('-')[1]
                            sellResult, myOrderHistory, openOrders = sellCoin(coinName, SELL_PRICE_RATE)
                            break

                dict_price.update({self.MarketName: [list_priv, list_curr, True]})

            except:
                print(self.MarketName + ' : error')
                traceback.print_exc()
                break
            
            time.sleep(1.1)

def buyCoin(coinName, rate):
    #coinName = 'BTC-'+coinName
    ticker = bittrex.get_ticker(coinName)
    askPrice = float(ticker['result']['Ask']) * rate
    #askPrice = '%.8f' % float(askPrice)
    qty = round(float(BUY_COIN_UNIT / askPrice), 8)
    printt('BUY - ' + coinName + ':' + str('%.8f' % askPrice) + ':' + str('%.8f' % qty))
    buyResult = bittrex.buy_limit(coinName, qty, askPrice)['result']
    myOrderHistory = bittrex.get_order_history(coinName, 1)
    openOrders = bittrex.get_open_orders(coinName)
    return askPrice, buyResult, myOrderHistory, openOrders

def sellCoin(coinName, rate):
    #{'success': True, 'message': '', 'result': {'Currency': 'ANS', 'Balance': None, 'Available': None, 'Pending': None, 'CryptoAddress': None}}
    printt('sellCoin :' + coinName)
    # number of coin
    balance = bittrex.get_balance(coinName)
    count = 0
    while balance['result']['Available']  == None:
        balance = bittrex.get_balance(coinName)
        time.sleep(0.1)
        count += 1
        if count == 100:
            break

    coinAvail = '%.10f' % float(balance['result']['Available'])
    print('sell qty : ' + coinAvail)
    # buy actual price
    history = bittrex.get_order_history('BTC-'+ coinName, 0)
    buy_actual_price = history['result'][0]['PricePerUnit']

    bidPrice = '%.8f' % (buy_actual_price * rate)
    print('sell price : ' + bidPrice)
    buyResult = bittrex.sell_limit('BTC-' + coinName, coinAvail, bidPrice)['result']
    myOrderHistory = bittrex.get_order_history(coinName, 1)
    openOrders = bittrex.get_open_orders(coinName)
    return buyResult, myOrderHistory, openOrders

def printt(str):
    currnet_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(currnet_time + ' - ' + str)
    writeLogFile(str)

def writeLogFile(str):
    currnet_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logfileName = currnet_time[:10].replace('-', '') + '.log'

    f = open('.\\logs\\' + logfileName, 'a')

    f.writelines(currnet_time+ ' - ' + str + '\n')
    f.close()

    #'2017-04-16 14:57:33'
    return 0

#coinName = sys.argv[1].upper()
#print(coinName)
#askPrice, buyResult, myOrderHistory, openOrders = buyCoin(coinName,1.2)
#print(str(buyResult))

#sellResult, myOrderHistory, openOrders = sellCoin(coinName,askPrice, 2.5)
#print(str(sellResult))
"""
MarketName = 'BTC-CFI'
askPrice, buyResult, myOrderHistory, openOrders = buyCoin(MarketName, BUY_PRICE_RATE)
coinName = MarketName[-3:]
sellResult, myOrderHistory, openOrders = sellCoin(coinName, askPrice, SELL_PRICE_RATE)
"""


result = bittrex.get_markets()

#print(result)

for coin in result['result']:
    MarketName = coin['MarketName']
    if 'BTC-' in MarketName and coin['IsActive'] and MarketName != 'BTC-MGO':
        try:
            #ticker = bittrex.get_ticker(MarketName)
            #currency =  float('%.8f' % ticker['result']['Ask'])
            #print(ticker)
            #print(MarketName + ' : ' + str(currency))
            current_time = datetime.datetime.now()
            dict_price.update({MarketName:[[current_time,1],[current_time,1], True]})
            ThreadGetTiker(MarketName).start()
        except:
            print('error : ' + MarketName)
            #print(MarketName + ' : ' + str(currency))
while True:
    printt('Program is running')
    for key, value in dict_price.items():
        #print(key + ' : ' + str('%.8f' % (value[0][1]-value[1][1])/value[0][1]))
        if value[0][0] != 0 and value[2]:
            rate = (value[1][1]-value[0][1])/value[0][1]
            value_str = '[%s][%.8f],[%s][%.8f]' % (value[0][0], value[0][1], value[1][0], value[1][1])
            #printt(key + ' : ' + value_str +' : '+ str('%.8f' % rate))
            writeLogFile(key.split('-')[1] + ' : ' + value_str + ' : ' + str('%.8f' % rate))
            if rate > ACCEPT_PRICE_GAP :
                printt('#################################### ' + key.split('-')[1] + ' #############################')
                printt('#################################### ' + key.split('-')[1] + ' #############################')
                printt(key.split('-')[1] + ' : ' + value_str + ' : ' + str('%.8f' % rate))
                printt('#################################### ' + key.split('-')[1] + ' #############################')
                printt('#################################### ' + key.split('-')[1] + ' #############################')
                writeLogFile(key.split('-')[1] + ' : ' + value_str + ' : ' + str('%.8f' % rate))
                writeLogFile('#################################### ' + key.split('-')[1] + ' #############################')


    time.sleep(3)
#print(result)
#print(str(myOrderHistory))
#print(str(openOrders))
