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
from multiprocessing import Process, Queue
slack = slackweb.Slack(url="https://hooks.slack.com/services/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")

with open("run_param_bittrex.json") as run_param_yobit:
    param = json.load(run_param_yobit)
    run_param_yobit.close()

# set in run_param_yobit.json file
# AUTO_TRADE = False  # True or False ex)False = Display CoinName Only
# BUY_COIN_UNIT = 0.0002  # Total Buy bit at least 0.0001 ex)0.1 = 0.1BIT
# ACCEPT_PRICE_GAP = 0.10  # Gap of prev between curr price ex)0.1 = 10%
# IGNORE_GAP_SECONDS = 5  # accept time gap under 10 ex)10 = 10 second
# BUY_PRICE_RATE = 1.01  # Buy coin at Current price * 1.2 ex)1.2 = 120%
# SELL_PRICE_RATE = 1.02  # Sell coin at buy price(Actual) * 1.2 ex)1.2 = 120%
# CANCEL_TIME = 60 # afert CANCLE_TIME seconds, cancel all open order and sell market ex) 50 = 50 seconds

AUTO_TRADE = param['AUTO_TRADE']
BUY_COIN_UNIT = param['BUY_COIN_UNIT']
ACCEPT_PRICE_GAP = param['ACCEPT_PRICE_GAP']
IGNORE_GAP_SECONDS = param['IGNORE_GAP_SECONDS']
BUY_PRICE_RATE = param['BUY_PRICE_RATE']
SELL_PRICE_RATE = param['SELL_PRICE_RATE']
LAST_SELL_PRICE_RATE = param['LAST_SELL_PRICE_RATE']
CANCEL_TIME = param['CANCEL_TIME']

with open("secrets_bittrex.json") as secrets_file:
    secrets = json.load(secrets_file)
    secrets_file.close()
    bittrex = Bittrex(secrets['key'], secrets['secret'])


dict_ALL_COIN_DATA = {}

class ThreadGetTiker(Thread):
    def __init__(self, coinName):
        self.coinName = coinName
        threading.Thread.__init__(self)

    def run(self):
        while True:
            try:
                ticker = bittrex.get_ticker(self.coinName)
                dict_ALL_COIN_DATA[self.coinName].setCurrentPrice(ticker['result']['Last'], ticker['result']['Bid'], ticker['result']['Ask'])
            except:
                print(self.coinList + ' : error')
                traceback.print_exc()



            time.sleep(1.1)

class ProcessManager:

    def __init__(self,list_coinName):
        self.dict_coinName = list_coinName
        for coinName in list_coinName:
            coin = Coin(coinName)
            dict_ALL_COIN_DATA.update({coinName: coin})

        process = Process(target=get_ticker, args=(bittrex, list_coinName))
        process.start()

def get_ticker(pbittrex, list_coinName):
    for coin in list_coinName:
        ThreadGetTiker(coin).start()

    while True:
        time.sleep(100)


class Coin:

    def __init__(self, coinName):
        curr_time = datetime.datetime.now()
        self.coinName = coinName
        # [curr_time, last_price, bid_price, ask_price]
        self.list_price = [[int(time.time()), 9999, 9999, 9999],
                           [int(time.time()), 9999, 9999, 9999],
                           [int(time.time()), 9999, 9999, 9999],
                           [int(time.time()), 9999, 9999, 9999],
                           [int(time.time()), 9999, 9999, 9999]
                           ]
        self.server_time = 0
        self.IsInTrading = False
        self.IsAutoTrad = True

    def setCurrentPrice(self, last_price, buy_price, sell_price):
        curr_time = datetime.datetime.now()

        #if self.list_price[4][1] != last_price:
        self.list_price[0] = self.list_price[1]
        self.list_price[1] = self.list_price[2]
        self.list_price[2] = self.list_price[3]
        self.list_price[3] = self.list_price[4]

        #datetime.datetime.fromtimestamp(server_time)
        self.list_price[4] = [int(time.time()), last_price, buy_price, sell_price]

        printt("%s : [%s : %.8f]->[%s : %.8f]->[%s : %.8f]->[%s : %.8f]->[%s : %.8f]" % (self.coinName,
                                                                               str(datetime.datetime.fromtimestamp(
                                                                                   self.list_price[0][0])),
                                                                               self.list_price[0][3],
                                                                               str(datetime.datetime.fromtimestamp(
                                                                                   self.list_price[1][0])),
                                                                               self.list_price[1][3],
                                                                               str(datetime.datetime.fromtimestamp(
                                                                                   self.list_price[2][0])),
                                                                               self.list_price[2][3],
                                                                               str(datetime.datetime.fromtimestamp(
                                                                                   self.list_price[3][0])),
                                                                               self.list_price[3][3],
                                                                               str(datetime.datetime.fromtimestamp(
                                                                                   self.list_price[4][0])),
                                                                               self.list_price[4][3]
                                                                               ))
        #self.catch_for_buy()
        time.sleep(0.01)

    def catch_for_buy(self):

        prev_prev_time = self.list_price[2][0]
        prev_time = self.list_price[3][0]
        curr_time = self.list_price[4][0]
        prev_price_last = self.list_price[3][1]
        curr_price_last = self.list_price[4][1]

        prev_price_bid = self.list_price[3][2]
        curr_price_bid = self.list_price[4][2]

        prev_price_ask = self.list_price[3][3]
        curr_price_ask = self.list_price[4][3]


        if self.IsInTrading == False:
            if curr_time - prev_prev_time < IGNORE_GAP_SECONDS:

                price_gap_rate_bid = (curr_price_bid - prev_price_bid) / prev_price_bid
                price_gap_rate_ask = (curr_price_ask - prev_price_ask) / prev_price_ask
                price_gap_rate_last = (curr_price_last - prev_price_last) / prev_price_last


                if price_gap_rate_last > 0.01:

                    prev3_prev_time = self.list_price[0][0]
                    prev2_prev_time = self.list_price[1][0]
                    prev_prev_time = self.list_price[2][0]
                    prev_curr_time = self.list_price[3][0]

                    prev3_prev_price_last = self.list_price[0][1]
                    prev2_prev_price_last = self.list_price[1][1]
                    prev_prev_price_last = self.list_price[2][1]
                    prev_curr_price_last = self.list_price[3][1]

                    if price_gap_rate_ask > ACCEPT_PRICE_GAP :
                        printt('%s : Catch #############\n' % self.coinName)

                        if AUTO_TRADE and self.IsAutoTrad:
                            self.IsAutoTrad = False
                            self.IsInTrading = True
                            ThreadTrade(self.coinName, curr_price_bid, SELL_PRICE_RATE, price_gap_rate_last).start()

                            slack_message = 'AUTO TRADE : [' + self.coinName + '] ' + '\nPREV: ' + str(datetime.datetime.fromtimestamp(prev_prev_time)) + ' , ' + str(
                                '%.8f' % prev_prev_price_last) + '\nCURR: ' + str(datetime.datetime.fromtimestamp(curr_time)) + ' , ' + str(
                                '%.8f' % curr_price_last) + '\nGAP: ' + '%.1f' % (
                                ACCEPT_PRICE_GAP * 100) + '\nUNIT: ' + '%.3f' % BUY_COIN_UNIT + 'BTC\nHOST: ' + socket.gethostname() + '\nCATCH : %0.8f' % price_gap_rate_last + '\nBUY_PRICE_RATE : %.2f' % BUY_PRICE_RATE + '\nSELL_PRICE_RATE : %.2f' % SELL_PRICE_RATE

                            #printt(slack_message)
                            slack.notify(text=slack_message)

                        elif AUTO_TRADE and self.IsAutoTrad != True:
                            printt('%s : Catch but is already traded\n' % self.coinName)

                        slack_message = '[' + self.coinName + '] ' + '\nPREV: ' + str(
                            datetime.datetime.fromtimestamp(prev_prev_time)) + ' , ' + str(
                            '%.8f' % prev_prev_price_last) + '\nCURR: ' + str(
                            datetime.datetime.fromtimestamp(curr_time)) + ' , ' + str(
                            '%.8f' % curr_price_last) + '\nGAP: ' + '%.1f' % (
                            ACCEPT_PRICE_GAP * 100) + '\nUNIT: ' + '%.3f' % BUY_COIN_UNIT + 'BTC\nHOST: ' + socket.gethostname() + '\nCATCH : %0.8f' % price_gap_rate_last + '\nBUY_PRICE_RATE : %.2f' % BUY_PRICE_RATE + '\nSELL_PRICE_RATE : %.2f' % SELL_PRICE_RATE

                        #printt(slack_message)
                        slack.notify(text=slack_message)

                    printt('%s Last: %.8f -> %.8f -> %.8f -> %.8f -> %.8f : %.8f' % (self.coinName,
                                                                                                         prev3_prev_price_last,
                                                                                                         prev2_prev_price_last,
                                                                                                         prev_prev_price_last,
                                                                                                         prev_curr_price_last,
                                                                                                         curr_price_last,
                                                                                                         price_gap_rate_last
                                                                                                         ))
                    #
                    # printt('%s : [%s:%.8f] -> [%s:%.8f] : %.8f' % (
                    #     self.coinName, str(datetime.datetime.fromtimestamp(prev3_prev_time)), prev3_prev_price_last,
                    #     str(datetime.datetime.fromtimestamp(prev2_prev_time)), prev2_prev_price_last, prev3_price_gap_rate_last))
                    #
                    # printt('%s : [%s:%.8f] -> [%s:%.8f] : %.8f' % (
                    #     self.coinName, str(datetime.datetime.fromtimestamp(prev2_prev_time)), prev2_prev_price_last,
                    #     str(datetime.datetime.fromtimestamp(prev_prev_time)), prev_prev_price_last, prev2_price_gap_rate_last))
                    #
                    # printt('%s : [%s:%.8f] -> [%s:%.8f] : %.8f' % (
                    #     self.coinName, str(datetime.datetime.fromtimestamp(prev_prev_time)), prev_prev_price_last,
                    #     str(datetime.datetime.fromtimestamp(prev_curr_time)), prev_curr_price_last, prev_price_gap_rate_last))
                    #
                    # printt('%s : [%s:%.8f] -> [%s:%.8f] : %.8f' % (
                    #     self.coinName, str(datetime.datetime.fromtimestamp(prev_time)), prev_price_last,
                    #     str(datetime.datetime.fromtimestamp(curr_time)), curr_price_last, price_gap_rate_last))

                    printt('%s Bid : %.8f -> %.8f -> %.8f -> %.8f -> %.8f : %.8f' % (self.coinName,
                                                                               self.list_price[0][2],
                                                                               self.list_price[1][2],
                                                                               self.list_price[2][2],
                                                                               self.list_price[3][2],
                                                                               self.list_price[4][2], (self.list_price[4][2]-self.list_price[3][2])/ self.list_price[3][2]))
                    printt('%s Ask : %.8f -> %.8f -> %.8f -> %.8f -> %.8f : %.8f' % (self.coinName,
                                                                               self.list_price[0][3],
                                                                               self.list_price[1][3],
                                                                               self.list_price[2][3],
                                                                               self.list_price[3][3],
                                                                               self.list_price[4][3], (self.list_price[4][3]-self.list_price[3][3])/ self.list_price[3][3]))

                    printt('%s volume : %.8f -> %.8f -> %.8f -> %.8f -> %.8f  : %.8f\n' % (self.coinName,
                                                                               self.list_price[0][8],
                                                                               self.list_price[1][8],
                                                                               self.list_price[2][8],
                                                                               self.list_price[3][8],
                                                                               self.list_price[4][8], (self.list_price[4][8]-self.list_price[3][8])/ self.list_price[3][8]))

    def print_price(self, str):
        printt('########################### ' + str + ' #############################')

        printt('%s Last: %.8f -> %.8f -> %.8f -> %.8f -> %.8f : %.8f' % (self.coinName,
                                                                         self.list_price[0][1],
                                                                         self.list_price[1][1],
                                                                         self.list_price[2][1],
                                                                         self.list_price[3][1],
                                                                         self.list_price[4][1], (
                                                                         self.list_price[4][1] - self.list_price[3][
                                                                             1]) / self.list_price[3][1]))

        printt('%s Bid : %.8f -> %.8f -> %.8f -> %.8f -> %.8f : %.8f' % (self.coinName,
                                                                         self.list_price[0][2],
                                                                         self.list_price[1][2],
                                                                         self.list_price[2][2],
                                                                         self.list_price[3][2],
                                                                         self.list_price[4][2], (
                                                                         self.list_price[4][2] - self.list_price[3][
                                                                             2]) / self.list_price[3][2]))
        printt('%s Ask : %.8f -> %.8f -> %.8f -> %.8f -> %.8f : %.8f' % (self.coinName,
                                                                         self.list_price[0][3],
                                                                         self.list_price[1][3],
                                                                         self.list_price[2][3],
                                                                         self.list_price[3][3],
                                                                         self.list_price[4][3], (
                                                                         self.list_price[4][3] - self.list_price[3][
                                                                             3]) / self.list_price[3][3]))

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
            coinName = self.MarketName.split('_')[0]
            sellResult = sellCoin(coinName, self.sell_rate)
            #time.sleep(60)
            coin = dict_ALL_COIN_DATA[self.MarketName]
            coin.IsInTrading = False;
            printt(self.MarketName + ' Trading END!! without Error')
        except:
            printt(self.MarketName + ' : error')
            coin.IsInTrading = False;
            printt(self.MarketName + ' Trading END!! with Error')
            traceback.print_exc()



def buyCoin(coinName, rate, curr_price):
    askPrice = curr_price * rate
    qty = round(float(BUY_COIN_UNIT / askPrice), 8)
    printt('BUY - ' + coinName + ':' + str('%.8f' % askPrice) + ':' + str('%.8f' % qty))
    buyResult = bittrex.buy_limit(coinName, qty, askPrice)['result']

    return buyResult


def sellCoin(coinName, rate):
    start_time = datetime.datetime.now()
    # {'success': True, 'message': '', 'result': {'Currency': 'ANS', 'Balance': None, 'Available': None, 'Pending': None, 'CryptoAddress': None}}
    printt('sellCoin :' + coinName)
    # number of coin
    balance = bittrex.get_balance(coinName)
    loop_count = 0
    sell_count = 0

    bidPrice = 0

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
                #bidPrice = '%.8f' % (0.0006 / float(coinAvail))
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
            loop_count2 = 0
            while True:
                openOrder = bittrex.get_open_orders('BTC-' + coinName)
                for order in openOrder['result']:
                    bittrex.cancel(order['OrderUuid'])
                    printt('BTC-' + coinName + ' CANCEL : ' + order['OrderUuid'])

                balance = bittrex.get_balance(coinName)

                if balance['result']['Available'] != None and balance['result']['Available'] != 0.0:
                    coinAvail = '%.8f' % float(balance['result']['Available'])
                    bidPrice = '%.8f' % (0.0006 / float(coinAvail))
                    printt('sell price : ' + bidPrice + ', sell unit : ' +  coinAvail)
                    sellResult = bittrex.sell_limit('BTC-' + coinName, coinAvail, bidPrice)['result']

                loop_count2 += 1

                printt("After %d seconds Try %d / 20 to Cancel and Sell Market Price" % (CANCEL_TIME, loop_count2))
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
    logfileName = currnet_time[:10].replace('-', '') + '_bittrex.log'

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

# def get_ticker(pbittrex, coinName, ALL_COIN_DATA):
#     while True:
#         ticker = pbittrex.get_ticker(coinName)
#         #print(str(result))
#         ALL_COIN_DATA[coinName].setCurrentPrice(ticker['result']['Last'], ticker['result']['Bid'], ticker['result']['Ask'])

if __name__  == "__main__":
    result = bittrex.get_markets()

    #printt(str(result))
    index = 0
    for idx, Market in enumerate(result['result']):
        coinName = Market['MarketName']
        if 'BTC-' in coinName and Market['IsActive'] and isExcludedCoin(coinName) is not True:
            list_coinName =[]
            if idx % 10 == 0:
                list_coinName.append(coinName)

            try:
                #qresult = Queue()
                processManager = ProcessManager(list_coinName)
            except:
                print('error : ' + list_coinName)

    if idx % 10 != 0:
        processManager = ProcessManager(list_coinName)


