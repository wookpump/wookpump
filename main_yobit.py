import time
from bittrex import Bittrex
from yobit import Yobit
import json
from decimal import *
import sys
import threading
from threading import Thread
import datetime
import traceback
import slackweb
import socket
import platform
import os

slack = slackweb.Slack(url="https://hooks.slack.com/services/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")

AUTO_TRADE = False  # True or False ex)False = Display CoinName Only
BUY_COIN_UNIT = 0.0002  # Total Buy bit at least 0.0001 ex)0.1 = 0.1BIT
ACCEPT_PRICE_GAP = 0.10  # Gap of prev between curr price ex)0.1 = 10%
IGNORE_GAP_SECONDS = 5  # accept time gap under 10 ex)10 = 10 second
BUY_PRICE_RATE = 1.01  # Buy coin at Current price * 1.2 ex)1.2 = 120%
SELL_PRICE_RATE = 1.02  # Sell coin at buy price(Actual) * 1.2 ex)1.2 = 120%
CANCEL_TIME = 60 # afert CANCLE_TIME seconds, cancel all open order and sell market ex) 50 = 50 seconds

dict_price = {} #dict_price.update({MarketName: [[prev_time, prev_price], [curr_time, curr_price], RunThread, AutoTrade]})
dict_price_bid = {}
dict_price_last = {}

dict_TradingThread = {}

with open("secrets.json") as secrets_file:
    secrets = json.load(secrets_file)
    secrets_file.close()
    bittrex = Bittrex(secrets['key'], secrets['secret'])

with open("secrets_yobit.json") as secrets_file:
    secrets = json.load(secrets_file)
    secrets_file.close()
    yobit = Yobit(secrets['key'], secrets['secret'])

class ThreadKeyInput(Thread):

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        while True:
            s = input()
            if s == 'q':
                exit(0)

class ThreadTrade(Thread):

    def __init__(self, MarketName, buy_price,sell_rate, catch_gap):
        self.MarketName = MarketName
        self.buy_price = buy_price
        self.catch_gap = catch_gap
        self.sell_rate = sell_rate
        threading.Thread.__init__(self)

    def run(self):
        try:
            printt(self.MarketName + ' Trading START!!')
            buyResult = buyCoin(self.MarketName, BUY_PRICE_RATE, self.buy_price)
            #printt(str(buyResult))
            coinName = self.MarketName.split('_')[0]
            sellResult = sellCoin(coinName, self.sell_rate)
            #printt(str(sellResult))
            t = dict_TradingThread[self.MarketName]
            t.inTrading = False;
            printt(self.MarketName + ' Trading END!!')
        except:
            printt(self.MarketName + ' : error')
            traceback.print_exc()

class ThreadGetTiker(Thread):
    def __init__(self, MarketName):
        self.MarketName = MarketName
        self.RunThread = True
        self.StopAutoTrade = False
        self.inTrading = False
        threading.Thread.__init__(self)

    def run(self):
        while dict_price[self.MarketName][2]:
            try:
                current_time = datetime.datetime.now()
                current_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ticker = yobit.get_ticker(self.MarketName)
                if ticker['result']['Bid'] < 0.00000100 or ticker['result']['Ask'] < 0.00000100 or ticker['result']['Last'] < 0.00000100 or ticker['result']['Ask'] > 0.1:
                    dict_price.update({self.MarketName: [[current_time, 1], [current_time, 1], False]})
                    dict_price_bid.update({self.MarketName: [[current_time, 1], [current_time, 1], False]})
                    dict_price_last.update({self.MarketName: [[current_time, 1], [current_time, 1], False]})
                    break
                price = float(ticker['result']['Ask'])
                price_bid = float(ticker['result']['Bid'])
                price_last = float(ticker['result']['Last'])

                list_priv = dict_price[self.MarketName][1]
                list_curr = [current_time, price]

                list_priv_bid = dict_price_bid[self.MarketName][1]
                list_curr_bid = [current_time, price_bid]

                list_priv_last = dict_price_last[self.MarketName][1]
                list_curr_last = [current_time, price_last]
                # print(self.MarketName + ' : ' + str(price))

                priv_price = list_priv[1]
                curr_price = list_curr[1]

                priv_price_bid = list_priv_bid[1]
                curr_price_bid = list_curr_bid[1]

                priv_price_last = list_priv_last[1]
                curr_price_last = list_curr_last[1]

                # Check Time gap
                priv_time = dict_price[self.MarketName][0][0]
                curr_time = dict_price[self.MarketName][1][0]
                gap_seconds = (curr_time - priv_time).total_seconds()

                if gap_seconds < IGNORE_GAP_SECONDS:
                    # check price gap
                    gap_price_rate = (curr_price - priv_price) / priv_price
                    gap_price_rate_bid = (curr_price_bid - priv_price_bid) / priv_price_bid
                    gap_price_rate_last = (curr_price_last - priv_price_last) / priv_price_last

                    if gap_price_rate > ACCEPT_PRICE_GAP :
                        # and gap_price_rate_bid > ACCEPT_PRICE_GAP and gap_price_rate_last > ACCEPT_PRICE_GAP:
                        printt('#################################### ' + self.MarketName.split('_')[0] + ' #############################')

                        value_str = 'ASK -  [%s][%.8f],[%s][%.8f]' % (priv_time, priv_price, curr_time, curr_price)
                        value_str_bid = 'BID -  [%s][%.8f],[%s][%.8f]' % (priv_time, priv_price_bid, curr_time, curr_price_bid)
                        value_str_last = 'LAST - [%s][%.8f],[%s][%.8f]' % (priv_time, priv_price_last, curr_time, curr_price_last)

                        printt(self.MarketName + ' : ' + value_str + ' : ' + str('%.8f' % gap_price_rate))
                        printt(self.MarketName + ' : ' + value_str_bid + ' : ' + str('%.8f' % gap_price_rate_bid))
                        printt(self.MarketName + ' : ' + value_str_last + ' : ' + str('%.8f' % gap_price_rate_last))

                        printt('#################################### ' + self.MarketName.split('_')[0] + ' #############################')

                        # Real Trading
                        if AUTO_TRADE and self.StopAutoTrade == False:
                            # close this coin
                            dict_price.update({self.MarketName: [list_priv, list_curr, False]})
                            printt('curr_price %.8f, BUY_PRICE_RATE %.8f' % (curr_price, BUY_PRICE_RATE))

                            sellRate = SELL_PRICE_RATE

                            # if gap_price_rate > 1.0:
                            #    sellRate = 2.0
                            # elif gap_price_rate > 0.5:
                            #    sellRate = 2.5

                            #Make Trade Thread
                            ThreadTrade(self.MarketName,curr_price,sellRate, gap_price_rate).start()
                            self.StopAutoTrade = True
                            self.inTrading = True

                            slack_message = '[' + self.MarketName + '] ' + '\nPREV: ' + priv_time.strftime(
                                '%m/%d %H:%M:%S') + ' , ' + str('%.8f' % priv_price) + '\nCURR: ' + curr_time.strftime(
                                '%m/%d %H:%M:%S') + ' , ' + str('%.8f' % curr_price) + '\nGAP: ' + '%.1f' % (
                                ACCEPT_PRICE_GAP * 100) + '\nUNIT: ' + '%.3f' % BUY_COIN_UNIT + 'BTC\nHOST: ' + socket.gethostname() + '\nCATCH : %0.8f' % gap_price_rate + '\nBUY_PRICE_RATE : %.2f' % BUY_PRICE_RATE + '\nSELL_PRICE_RATE : %.2f' % sellRate

                            printt(slack_message)
                            slack.notify(text=slack_message)

                        if self.inTrading:
                            value_str = 'ASK -  [%s][%.8f],[%s][%.8f]' % (priv_time, priv_price, curr_time, curr_price)
                            value_str_bid = 'BID -  [%s][%.8f],[%s][%.8f]' % (
                            priv_time, priv_price_bid, curr_time, curr_price_bid)
                            value_str_last = 'LAST - [%s][%.8f],[%s][%.8f]' % (
                            priv_time, priv_price_last, curr_time, curr_price_last)

                            printt(self.MarketName + ' : ' + value_str + ' : ' + str('%.8f' % gap_price_rate))
                            printt(self.MarketName + ' : ' + value_str_bid + ' : ' + str('%.8f' % gap_price_rate_bid))
                            printt(self.MarketName + ' : ' + value_str_last + ' : ' + str('%.8f' % gap_price_rate_last))


                        slack_message = '[' + self.MarketName + '] ' + '\nPREV: ' + priv_time.strftime(
                            '%m/%d %H:%M:%S') + ' , ' + str('%.8f' % priv_price) + '\nCURR: ' + curr_time.strftime(
                            '%m/%d %H:%M:%S') + ' , ' + str('%.8f' % curr_price) + '\nGAP: ' + '%.1f' % (
                            ACCEPT_PRICE_GAP * 100) + '\nUNIT: ' + '%.3f' % BUY_COIN_UNIT + 'BTC\nHOST: ' + socket.gethostname() + '\nCATCH : %0.8f' % gap_price_rate + '\nBUY_PRICE_RATE : %.2f' % BUY_PRICE_RATE + '\nSELL_PRICE_RATE : %.2f' % SELL_PRICE_RATE

                        slack.notify(text=slack_message)

                dict_price.update({self.MarketName: [list_priv, list_curr, True]})
                dict_price_bid.update({self.MarketName: [list_priv_bid, list_curr_bid, True]})
                dict_price_last.update({self.MarketName: [list_priv_last, list_curr_last, True]})

            except:
                print(self.MarketName + ' : error')
                traceback.print_exc()



            time.sleep(1.1)


def buyCoin(coinName, rate, curr_price):
    askPrice = curr_price * rate
    qty = round(float(BUY_COIN_UNIT / askPrice), 8)
    printt('BUY - ' + coinName + ':' + str('%.8f' % askPrice) + ':' + str('%.8f' % qty))
    buyResult = yobit.buy_limit(coinName, qty, askPrice)
    #printt(str(buyResult))
    return buyResult


def sellCoin(coinName, rate):
    sellResult = ''
    start_time = datetime.datetime.now()
    # {'success': True, 'message': '', 'result': {'Currency': 'ANS', 'Balance': None, 'Available': None, 'Pending': None, 'CryptoAddress': None}}
    printt('sellCoin :' + coinName)
    # number of coin
    loop_count = 0
    sell_count = 0

    bidPrice = 0

    balance = yobit.get_balance(coinName)
    while True:
        if balance['result']['Available'] == None or balance['result']['Available'] == 0.0:
            balance = yobit.get_balance(coinName)
        else:
            if sell_count == 0:
                coinAvail = float(balance['result']['Available'])
                history = yobit.get_order_history_type(coinName + '_btc', 10, 'buy')
                buy_actual_price = history['result'][0]['PricePerUnit']
                bidPrice = buy_actual_price * rate
                if coinAvail * bidPrice < 0.0001:
                    bidPrice = 0.0001 / float(coinAvail)

                sellResult = yobit.sell_limit(coinName + '_btc', coinAvail, bidPrice)
                #printt('D3' + str(sellResult))
                printt('sell price : %.8f' % bidPrice + ', sell unit : %.8f' % coinAvail + ', sell_count %d' % sell_count)
                sell_count += 1
            else:
                coinAvail = float(balance['result']['Available'])
                #bidPrice = 0.0001 / float(coinAvail)

                sellResult = yobit.sell_limit(coinName + '_btc', coinAvail, bidPrice)
                #printt('D2' + str(sellResult))
                printt('sell price : %.8f' % bidPrice + ', sell unit : %.8f' % coinAvail + ', sell_count %d' % sell_count)
                sell_count += 1

        loop_count += 1
        time.sleep(0.1)
        if loop_count >= 100:
            printt("LOOP COUNT 100 BREAK")
            break

        curr_time  = datetime.datetime.now()
        during_seconds = (curr_time - start_time).total_seconds()

        if during_seconds > CANCEL_TIME:
            loop_count2 = 0
            list_newOrderId = []
            while True:
                openOrder = yobit.get_open_orders(coinName + '_btc')
                for order in openOrder['result']:
                    order_id = order['OrderUuid']
                    #print(str(order_id) + ' in ' + str(list_newOrderId))
                    #print(str(order_id in list_newOrderId))
                    if str(order_id) in list_newOrderId:
                        continue
                    else:
                        result = yobit.cancel(order_id)
                        #sprintt('Cancel : ' + str(result))
                        printt(coinName + '_btc' + ' CANCEL : ' + order['OrderUuid'])

                balance = yobit.get_balance(coinName)

                if balance['result']['Available'] != None and balance['result']['Available'] != 0.0:
                    history = yobit.get_order_history_type(coinName + '_btc', 10, 'buy')
                    buy_actual_price = history['result'][0]['PricePerUnit']
                    coinAvail = float(balance['result']['Available'])
                    bidPrice = buy_actual_price * 1.1
                    if coinAvail * bidPrice < 0.0001:
                        bidPrice = 0.0001 / float(coinAvail)
                    sellResult = yobit.sell_limit(coinName + '_btc', coinAvail, bidPrice)
                    if sellResult['success'] == 1:
                        list_newOrderId.append(str(sellResult['return']['order_id']))
                    printt('sell price : %.8f' % bidPrice + ', sell unit : %.8f' % coinAvail)
                    #printt('D1' + str(sellResult))
                loop_count2 += 1

                printt("After %d seconds Try %d / 20 to Cancel and Sell 1.1" % (CANCEL_TIME, loop_count2))
                if(loop_count2 >= 20):
                    printt("LOOP COUNT2 10 BREAK")
                    break
            break

    return sellResult


def printt(str):
    currnet_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(currnet_time + ' - ' + str)
    writeLogFile(str)


def writeLogFile(str):
    currnet_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logfileName = currnet_time[:10].replace('-', '') + '.log'

    f = open('./logs/' + logfileName, 'a')

    f.writelines(currnet_time + ' - ' + str + '\n')
    f.close()

    return 0


def isExcludedCoin(MarketName):
    print("MarketName : " + MarketName)
    with open("excluded_coin_list.json") as f:
        excludedCoinName = json.load(f)
        if MarketName in excludedCoinName['coin']:
            print("Excluded")
            return True
        else:
            print("Included")
            return False

with open("include_coin_list_yobit.json") as secrets_file:
    coinList = json.load(secrets_file)

def main():
    #for coin in coinList:
    #    print(coin)
    result = yobit.get_markets()

    #printt(str(result))
    index = 0
    #for coin in result['result']:

    for coin in coinList['coin']:
        #MarketName = coin['MarketName']
        #if len(MarketName.split('_')[0]) > 4:
        #    continue
        MarketName = coin

        #if '_btc' in MarketName and coin['IsActive'] and isExcludedCoin(MarketName) is not True:
        current_time = datetime.datetime.now()
        dict_price.update({MarketName: [[current_time, 1], [current_time, 1], True, True]})
        dict_price_bid.update({MarketName: [[current_time, 1], [current_time, 1], True, True]})
        dict_price_last.update({MarketName: [[current_time, 1], [current_time, 1], True, True]})
        t = ThreadGetTiker(MarketName)
        t.start()
        dict_TradingThread.update({MarketName:t})
        index += 1
        printt(MarketName + ' is started : %d' % index)
        time.sleep(0.1)

    while True:
        """
        current_time = datetime.datetime.now()
        os_type = platform.system()
        if os_type == 'Linux':
            os.system('clear')
        elif os_type == 'Windows':
            os.system('cls')
        """
        printt(str(current_time) + ' : Program is running')

        for key, value in dict_price.items():
            # print(key + ' : ' + str('%.8f' % (value[0][1]-value[1][1])/value[0][1]))
            if value[0][0] != 0 and value[2]:
                price_bid = dict_price_bid[key]
                price_last = dict_price_last[key]

                rate = (value[1][1] - value[0][1]) / value[0][1]
                rate_bid = (price_bid[1][1] - price_bid[0][1]) / price_bid[0][1]
                rate_last = (price_bid[1][1] - price_bid[0][1]) / price_bid[0][1]

                value_str = 'ASK  - [%s][%.8f],[%s][%.8f]' % (value[0][0], value[0][1], value[1][0], value[1][1])
                value_str_bid = 'BID  - [%s][%.8f],[%s][%.8f]' % (price_bid[0][0], price_bid[0][1], price_bid[1][0], price_bid[1][1])
                value_str_last = 'LAST - [%s][%.8f],[%s][%.8f]' % (price_last[0][0], price_last[0][1], price_last[1][0], price_last[1][1])

                # printt(key + ' : ' + value_str +' : '+ str('%.8f' % rate))
                if AUTO_TRADE == False:
                    writeLogFile(key.split('_')[0] + ' : ' + value_str + ' : ' + str('%.8f' % rate))
                    writeLogFile(key.split('_')[0] + ' : ' + value_str_bid + ' : ' + str('%.8f' % rate_bid))
                    writeLogFile(key.split('_')[0] + ' : ' + value_str_last + ' : ' + str('%.8f' % rate_last))
                """
                if rate > ACCEPT_PRICE_GAP:
                    printt('#################################### ' + key.split('_')[0] + ' #############################')
                    printt('#################################### ' + key.split('_')[0] + ' #############################')
                    printt(key.split('_')[0] + ' : ' + value_str + ' : ' + str('%.8f' % rate))
                    printt(key.split('_')[0] + ' : ' + value_str_bid + ' : ' + str('%.8f' % rate_bid))
                    printt('#################################### ' + key.split('_')[0] + ' #############################')
                    printt('#################################### ' + key.split('_')[0] + ' #############################')
            """
        time.sleep(2)


if __name__  == "__main__":
    main()
