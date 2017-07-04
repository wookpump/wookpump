import time
from bittrex import Bittrex
import json
from decimal import *
import sys
import threading
from threading import Thread
import datetime
import traceback
import slackweb
import socket

slack = slackweb.Slack(url="https://hooks.slack.com/services/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")

AUTO_TRADE = False  # True or False ex)False = Display CoinName Only
BUY_COIN_UNIT = 0.001  # Total Buy bit ex)0.1 = 0.1BIT
ACCEPT_PRICE_GAP = 0.10  # Gap of prev between curr price ex)0.1 = 10%
IGNORE_GAP_SECONDS = 5  # accept time gap under 10 ex)10 = 10 second
BUY_PRICE_RATE = 1.5  # Buy coin at Current price * 1.2 ex)1.2 = 120%
SELL_PRICE_RATE = 3.0  # Sell coin at buy price(Actual) * 1.2 ex)1.2 = 120%
CANCEL_TIME = 30 # afert CANCLE_TIME seconds, cancel all open order and sell market ex) 50 = 50 seconds

dict_price = {}
dict_price_bid = {}
dict_price_last = {}
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

                    if gap_price_rate > ACCEPT_PRICE_GAP:
                        printt('#################################### ' + self.MarketName.split('-')[
                            1] + ' #############################')
                        price_ask = dict_price[self.MarketName]
                        price_bid = dict_price_bid[self.MarketName]
                        price_last = dict_price_last[self.MarketName]

                        value_str = 'ASK -  [%s][%.8f],[%s][%.8f]' % (price_ask[0][0], price_ask[0][1], price_ask[1][0], price_ask[1][1])
                        value_str_bid = 'BID -  [%s][%.8f],[%s][%.8f]' % (price_bid[0][0], price_bid[0][1], price_bid[1][0], price_bid[1][1])
                        value_str_last = 'LAST - [%s][%.8f],[%s][%.8f]' % (price_last[0][0], price_last[0][1], price_last[1][0], price_last[1][1])

                        printt(self.MarketName + ' : ' + value_str + ' : ' + str('%.8f' % gap_price_rate))
                        printt(self.MarketName + ' : ' + value_str_bid + ' : ' + str('%.8f' % gap_price_rate_bid))
                        printt(self.MarketName + ' : ' + value_str_last + ' : ' + str('%.8f' % gap_price_rate_last))

                        printt('#################################### ' + self.MarketName.split('-')[
                            1] + ' #############################')

                        # Real Trading
                        if AUTO_TRADE:
                            # close this coin
                            dict_price.update({self.MarketName: [list_priv, list_curr, False]})

                            buyResult = buyCoin(self.MarketName, BUY_PRICE_RATE, curr_price)
                            printt(str(buyResult))
                            coinName = self.MarketName.split('-')[1]

                            sellRate = SELL_PRICE_RATE

                            if gap_price_rate > 1.0:
                                sellRate = 2.0
                            elif gap_price_rate > 0.5:
                                sellRate = 2.5

                            sellResult = sellCoin(coinName, sellRate)
                            printt(str(sellResult))


                            slack_message = '[' + self.MarketName + '] ' + '\nPREV: ' + priv_time.strftime(
                                '%m/%d %H:%M:%S') + ' , ' + str('%.8f' % priv_price) + '\nCURR: ' + curr_time.strftime(
                                '%m/%d %H:%M:%S') + ' , ' + str('%.8f' % curr_price) + '\nGAP: ' + '%.1f' % (
                                ACCEPT_PRICE_GAP * 100) + '\nUNIT: ' + '%.3f' % BUY_COIN_UNIT + 'BTC\nHOST: ' + socket.gethostname() + '\nCATCH : %0.8f' % gap_price_rate + '\nBUY_PRICE_RATE : %.2f' % BUY_PRICE_RATE + '\nSELL_PRICE_RATE : %.2f' % sellRate

                            printt(slack_message)
                            slack.notify(text=slack_message)
                            break

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
    buyResult = bittrex.buy_limit(coinName, qty, askPrice)['result']

    return buyResult


def sellCoin(coinName, rate):
    # {'success': True, 'message': '', 'result': {'Currency': 'ANS', 'Balance': None, 'Available': None, 'Pending': None, 'CryptoAddress': None}}
    printt('sellCoin :' + coinName)
    # number of coin
    balance = bittrex.get_balance(coinName)
    loop_count = 0
    sell_count = 0
    start_time = datetime.datetime.now()
    while True:
        if balance['result']['Available'] == None or balance['result']['Available'] == 0.0:
            balance = bittrex.get_balance(coinName)
        else:
            if sell_count == 0:
                coinAvail = '%.8f' % float(balance['result']['Available'])
                history = bittrex.get_order_history('BTC-' + coinName, 0)
                buy_actual_price = history['result'][0]['PricePerUnit']
                bidPrice = '%.8f' % (buy_actual_price * rate)
                sellResult = bittrex.sell_limit('BTC-' + coinName, coinAvail, bidPrice)['result']
                printt('sell price : ' + bidPrice + ', sell unit : ' + coinAvail + ', sell_count %d' % sell_count)
                sell_count += 1
            else:
                coinAvail = '%.8f' % float(balance['result']['Available'])
                bidPrice = '%.8f' % (0.0006 / float(coinAvail))
                printt('sell price : ' + bidPrice + ', sell unit : ' + coinAvail + ', sell market price count %d' % sell_count)
                sellResult = bittrex.sell_limit('BTC-' + coinName, coinAvail, bidPrice)['result']
                sell_count += 1

        loop_count += 1
        time.sleep(0.1)
        if loop_count >= 100:
            printt("LOOP COUNT 100 BREAK")
            break

        curr_time  = datetime.datetime.now()
        during_seconds = (curr_time - start_time).total_seconds()

        if during_seconds > CANCEL_TIME:
            openOrder = bittrex.get_open_orders('BTC-' + coinName)
            for order in openOrder['result']:
                bittrex.cancel(order['OrderUuid'])
                printt('BTC-' + coinName + ' CANCEL : ' + order['OrderUuid'])

            balance = bittrex.get_balance(coinName)
            loop_count2 = 0

            while True:
                if balance['result']['Available'] == None or balance['result']['Available'] == 0.0:
                    balance = bittrex.get_balance(coinName)
                else:
                    coinAvail = '%.8f' % float(balance['result']['Available'])
                    bidPrice = '%.8f' % (0.0006 / float(coinAvail))
                    printt('sell price : ' + bidPrice + ', sell unit : ' +  coinAvail + ', sell market order after cancel %d' % loop_count2)
                    sellResult = bittrex.sell_limit('BTC-' + coinName, coinAvail, bidPrice)['result']

                loop_count2 += 1

                if(loop_count2 >= 10):
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

if __name__  == "__main__":
    result = bittrex.get_markets()

    printt(str(result))
    for coin in result['result']:
        MarketName = coin['MarketName']
        if 'BTC-' in MarketName and coin['IsActive'] and isExcludedCoin(MarketName) is not True:
            try:
                current_time = datetime.datetime.now()
                dict_price.update({MarketName: [[current_time, 1], [current_time, 1], True]})
                dict_price_bid.update({MarketName: [[current_time, 1], [current_time, 1], True]})
                dict_price_last.update({MarketName: [[current_time, 1], [current_time, 1], True]})
                ThreadGetTiker(MarketName).start()
            except:
                print('error : ' + MarketName)

    while True:
        printt('Program is running')
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
                writeLogFile(key.split('-')[1] + ' : ' + value_str + ' : ' + str('%.8f' % rate))
                writeLogFile(key.split('-')[1] + ' : ' + value_str_bid + ' : ' + str('%.8f' % rate_bid))
                writeLogFile(key.split('-')[1] + ' : ' + value_str_last + ' : ' + str('%.8f' % rate_last))
                """
                if rate > ACCEPT_PRICE_GAP:
                    printt('#################################### ' + key.split('-')[1] + ' #############################')
                    printt('#################################### ' + key.split('-')[1] + ' #############################')
                    printt(key.split('-')[1] + ' : ' + value_str + ' : ' + str('%.8f' % rate))
                    printt(key.split('-')[1] + ' : ' + value_str_bid + ' : ' + str('%.8f' % rate_bid))
                    printt('#################################### ' + key.split('-')[1] + ' #############################')
                    printt('#################################### ' + key.split('-')[1] + ' #############################')
            """
        time.sleep(3)
