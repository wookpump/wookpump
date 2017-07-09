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

# with open("secrets.json") as secrets_file:
#     secrets = json.load(secrets_file)
#     secrets_file.close()
#     bittrex = Bittrex(secrets['key'], secrets['secret'])

with open("secrets_yobit.json") as secrets_file:
    secrets = json.load(secrets_file)
    secrets_file.close()
    yobit = Yobit(secrets['key'], secrets['secret'])


with open("run_param_yobit.json") as run_param_yobit:
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

class Coin:

    def __init__(self, coinName):
        curr_time = datetime.datetime.now()
        self.coinName = coinName
        # [curr_time, last_price, buy_price, sell_price, server_time]
        # [curr_time, last_price, bid_price, ask_price, server_time]
        self.list_price = [[int(time.time()), 9999, 9999, 9999, int(time.time())],
                           [int(time.time()), 9999, 9999, 9999, int(time.time())],
                           [int(time.time()), 9999, 9999, 9999, int(time.time())],
                           [int(time.time()), 9999, 9999, 9999, int(time.time())],
                           [int(time.time()), 9999, 9999, 9999, int(time.time())]]
        self.update_serv_time = 0
        self.server_time = 0
        self.IsInTrading = False
        self.IsAutoTrad = True

    def setCurrentPrice(self, last_price, buy_price, sell_price, server_time):
        curr_time = datetime.datetime.now()

        if self.list_price[4][1] != last_price:
            self.list_price[0] = self.list_price[1]
            self.list_price[1] = self.list_price[2]
            self.list_price[2] = self.list_price[3]
            self.list_price[3] = self.list_price[4]

            #datetime.datetime.fromtimestamp(server_time)
            self.list_price[4] = [int(time.time()), last_price, buy_price, sell_price, server_time]

            self.catch_for_buy()
        else:
            self.list_price[4][0] = int(time.time())

    def catch_for_buy(self):

        prev_prev_time = self.list_price[2][0]
        prev_time = self.list_price[3][0]
        curr_time = self.list_price[4][0]
        prev_price_last = self.list_price[3][1]
        curr_price_last = self.list_price[4][1]

        curr_price_bid = self.list_price[4][2]
        curr_price_ask = self.list_price[4][3]

        if prev_price_last < 0.00000100 or prev_price_last > 0.1:
            return None

        if self.IsInTrading == False:
            if curr_time - prev_prev_time < IGNORE_GAP_SECONDS:

                price_gap_rate_last = (curr_price_last - prev_price_last) / prev_price_last

                if price_gap_rate_last > ACCEPT_PRICE_GAP:

                    prev_prev_time = self.list_price[2][0]
                    prev_curr_time = self.list_price[3][0]
                    prev_prev_price_last = self.list_price[2][1]
                    prev_curr_price_last = self.list_price[3][1]

                    prev_price_gap_rate_last = (prev_curr_price_last - prev_prev_price_last) / prev_prev_price_last

                    printt('%s : %.8f -> %.8f -> %.8f - %.8f -> %.8f' % (self.coinName, prev_prev_price_last, prev_curr_price_last, curr_price_last, prev_price_gap_rate_last, price_gap_rate_last))

                    printt('%s : [%s : %.8f]->[%s:%.8f] : %.8f' % (
                        self.coinName, str(datetime.datetime.fromtimestamp(prev_prev_time)), prev_prev_price_last,
                        str(datetime.datetime.fromtimestamp(prev_curr_time)), prev_curr_price_last, prev_price_gap_rate_last))

                    printt('%s : [%s : %.8f]->[%s:%.8f] : %.8f' % (
                        self.coinName, str(datetime.datetime.fromtimestamp(prev_time)), prev_price_last,
                        str(datetime.datetime.fromtimestamp(curr_time)), curr_price_last, price_gap_rate_last))

                    if prev_price_gap_rate_last > ACCEPT_PRICE_GAP:
                        printt('%s : Catch #############' % self.coinName)

                        if AUTO_TRADE and self.IsAutoTrad:
                            self.IsAutoTrad = False
                            self.IsInTrading = True
                            ThreadTrade(self.coinName, curr_price_bid, SELL_PRICE_RATE, price_gap_rate_last).start()

                            slack_message = '[' + self.MarketName + '] ' + '\nPREV: ' + str(datetime.datetime.fromtimestamp(prev_prev_time)) + ' , ' + str(
                                '%.8f' % prev_prev_price_last) + '\nCURR: ' + str(datetime.datetime.fromtimestamp(curr_time)) + ' , ' + str(
                                '%.8f' % curr_price_last) + '\nGAP: ' + '%.1f' % (
                                ACCEPT_PRICE_GAP * 100) + '\nUNIT: ' + '%.3f' % BUY_COIN_UNIT + 'BTC\nHOST: ' + socket.gethostname() + '\nCATCH : %0.8f' % price_gap_rate_last + '\nBUY_PRICE_RATE : %.2f' % BUY_PRICE_RATE + '\nSELL_PRICE_RATE : %.2f' % SELL_PRICE_RATE

                            printt(slack_message)
                            slack.notify(text=slack_message)

                        elif AUTO_TRADE and self.IsAutoTrad != True:
                            printt('%s : Catch but is already traded' % self.coinName)





dict_ALL_COIN_DATA = {}

dict_price = {} #dict_price.update({MarketName: [[prev_time, prev_price], [curr_time, curr_price], RunThread, AutoTrade]})
dict_price_bid = {}
dict_price_last = {}

dict_TradingThread = {}


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
            coinName = self.MarketName.split('_')[0]
            sellResult = sellCoin(coinName, self.sell_rate)
            #time.sleep(60)
            coin = dict_ALL_COIN_DATA[self.MarketName]
            coin.IsInTrading = False;
            printt(self.MarketName + ' Trading END!!')
        except:
            printt(self.MarketName + ' : error')
            traceback.print_exc()

class ThreadGetTiker(Thread):
    def __init__(self, coinList):
        self.coinList = coinList
        threading.Thread.__init__(self)

    def run(self):
        while True:
            try:
                result = yobit.get_ticker_bulk(self.coinList)
                # {'poke_btc': {'high': 9e-08, 'low': 2e-08, 'avg': 5e-08, 'vol': 1.70463987, 'vol_cur': 33515838.95793353, 'last': 4e-08, 'buy': 4e-08, 'sell': 5e-08, 'updated': 1499484058}, 'vene_btc': {'high': 2e-08, 'low': 2e-08, 'avg': 2e-08, 'vol': 0.03700625, 'vol_cur': 1850312.82435129, 'last': 2e-08, 'buy': 1e-08, 'sell': 2e-08, 'updated': 1499484062}, 'yay_btc': {'high': 2e-08, 'low': 1e-08, 'avg': 1e-08, 'vol': 0.02214616, 'vol_cur': 1177148.54292766, 'last': 2e-08, 'buy': 1e-08, 'sell': 2e-08, 'updated': 1499483981}, 'token_btc': {'high': 1e-08, 'low': 1e-08, 'avg': 1e-08, 'vol': 0.04069669, 'vol_cur': 4069671.71277445, 'last': 1e-08, 'buy': 0, 'sell': 1e-08, 'updated': 1499484056}, 'lir_btc': {'high': 1.1e-07, 'low': 1.1e-07, 'avg': 1.1e-07, 'vol': 0.01010008, 'vol_cur': 91819.09090908, 'last': 1.1e-07, 'buy': 1e-07, 'sell': 1.1e-07, 'updated': 1499484045}, 'putin_btc': {'high': 9.9e-07, 'low': 9.1e-07, 'avg': 9.5e-07, 'vol': 0.5875689, 'vol_cur': 625211.37812634, 'last': 9.5e-07, 'buy': 9.4e-07, 'sell': 9.5e-07, 'updated': 1499484049}, 'dck_btc': {'high': 5.6e-07, 'low': 5.6e-07, 'avg': 5.6e-07, 'vol': 0.00013043, 'vol_cur': 232.9245283, 'last': 5.6e-07, 'buy': 5.7e-07, 'sell': 5.8e-07, 'updated': 1499484025}, 'alc_btc': {'high': 4e-08, 'low': 3e-08, 'avg': 3e-08, 'vol': 0.000265, 'vol_cur': 8000, 'last': 3e-08, 'buy': 3e-08, 'sell': 4e-08, 'updated': 1499484079}, 'chemx_btc': {'high': 1.04e-06, 'low': 1.03e-06, 'avg': 1.03e-06, 'vol': 0.00442552, 'vol_cur': 4256.29621525, 'last': 1.04e-06, 'buy': 8.6e-07, 'sell': 1.04e-06, 'updated': 1499483968}, 'marv_btc': {'high': 1e-08, 'low': 1e-08, 'avg': 1e-08, 'vol': 0.00352453, 'vol_cur': 352453.99201596, 'last': 1e-08, 'buy': 0, 'sell': 1e-08, 'updated': 1499483994}, 'nic_btc': {'high': 2.4e-06, 'low': 1.79e-06, 'avg': 2.09e-06, 'vol': 0.00420886, 'vol_cur': 2028.90662582, 'last': 2.4e-06, 'buy': 1.81e-06, 'sell': 2.38e-06, 'updated': 1499484029}, 'chess_btc': {'high': 1.98e-06, 'low': 1.35e-06, 'avg': 1.66e-06, 'vol': 0.22747683, 'vol_cur': 159595.49845252, 'last': 1.42e-06, 'buy': 1.42e-06, 'sell': 1.63e-06, 'updated': 1499484049}, 'csmic_btc': {'high': 4.17e-06, 'low': 4.17e-06, 'avg': 4.17e-06, 'vol': 0, 'vol_cur': 0, 'last': 4.17e-06, 'buy': 3.87e-06, 'sell': 4.17e-06, 'updated': 1499484055}, 'radi_btc': {'high': 1.1e-07, 'low': 2e-08, 'avg': 6e-08, 'vol': 3.33843195, 'vol_cur': 57276396.82128312, 'last': 4e-08, 'buy': 3e-08, 'sell': 4e-08, 'updated': 1499484017}, 'gt_btc': {'high': 7e-08, 'low': 1e-08, 'avg': 4e-08, 'vol': 6.05165096, 'vol_cur': 195746882.68211088, 'last': 4e-08, 'buy': 3e-08, 'sell': 4e-08, 'updated': 1499484047}, 'ctl_btc': {'high': 4e-08, 'low': 1e-08, 'avg': 2e-08, 'vol': 4.74456789, 'vol_cur': 245059398.11808962, 'last': 2e-08, 'buy': 2e-08, 'sell': 3e-08, 'updated': 1499483982}, 'rpc_btc': {'high': 1.667e-05, 'low': 1.276e-05, 'avg': 1.471e-05, 'vol': 0.00245389, 'vol_cur': 190.61150545, 'last': 1.279e-05, 'buy': 1.279e-05, 'sell': 1.802e-05, 'updated': 1499483966}, 'frwc_btc': {'high': 3.5e-07, 'low': 3.5e-07, 'avg': 3.5e-07, 'vol': 0.00021246, 'vol_cur': 607.08525805, 'last': 3.5e-07, 'buy': 3.5e-07, 'sell': 3.8e-07, 'updated': 1499484054}, 'rust_btc': {'high': 6.15e-06, 'low': 4.2e-06, 'avg': 5.17e-06, 'vol': 0.00434915, 'vol_cur': 777.89685758, 'last': 4.21e-06, 'buy': 4.23e-06, 'sell': 6.15e-06, 'updated': 1499484046}, 'craft_btc': {'high': 3.5e-07, 'low': 3.5e-07, 'avg': 3.5e-07, 'vol': 0.00315, 'vol_cur': 9000, 'last': 3.5e-07, 'buy': 2.9e-07, 'sell': 3.5e-07, 'updated': 1499484083}, 'xt_btc': {'high': 1e-08, 'low': 1e-08, 'avg': 1e-08, 'vol': 0.00679732, 'vol_cur': 679733.57320206, 'last': 1e-08, 'buy': 0, 'sell': 1e-08, 'updated': 1499484059}, 'taj_btc': {'high': 2.58e-06, 'low': 1.8e-06, 'avg': 2.19e-06, 'vol': 0.01493815, 'vol_cur': 7322.59190985, 'last': 2.55e-06, 'buy': 1.82e-06, 'sell': 2.55e-06, 'updated': 1499484008}, 'nzc_btc': {'high': 2e-08, 'low': 1e-08, 'avg': 1e-08, 'vol': 0.00232086, 'vol_cur': 144934.97392487, 'last': 2e-08, 'buy': 1e-08, 'sell': 2e-08, 'updated': 1499484008}, 'cj_btc': {'high': 1e-07, 'low': 8e-08, 'avg': 9e-08, 'vol': 0.2545815, 'vol_cur': 2972775.3810998, 'last': 9e-08, 'buy': 8e-08, 'sell': 1e-07, 'updated': 1499483999}, 'artc_btc': {'high': 7.8e-07, 'low': 7.8e-07, 'avg': 7.8e-07, 'vol': 0.00035659, 'vol_cur': 457.17881097, 'last': 7.8e-07, 'buy': 7.9e-07, 'sell': 8.2e-07, 'updated': 1499484070}, 'ibank_btc': {'high': 1.1e-06, 'low': 9.5e-07, 'avg': 1.02e-06, 'vol': 0.02939222, 'vol_cur': 29044.6210733, 'last': 9.5e-07, 'buy': 9.5e-07, 'sell': 1.13e-06, 'updated': 1499484079}, 'scrpt_btc': {'high': 1.5e-07, 'low': 1.5e-07, 'avg': 1.5e-07, 'vol': 0.00170644, 'vol_cur': 11376.41600529, 'last': 1.5e-07, 'buy': 1.5e-07, 'sell': 1.6e-07, 'updated': 1499484008}, 'air_btc': {'high': 2e-08, 'low': 1e-08, 'avg': 1e-08, 'vol': 0.00601047, 'vol_cur': 491049.35672654, 'last': 1e-08, 'buy': 1e-08, 'sell': 2e-08, 'updated': 1499484089}, 'enter_btc': {'high': 1e-08, 'low': 1e-08, 'avg': 1e-08, 'vol': 0.00764607, 'vol_cur': 764607.07457391, 'last': 1e-08, 'buy': 0, 'sell': 1e-08, 'updated': 1499484028}, 'xpd_btc': {'high': 8.4e-07, 'low': 6.1e-07, 'avg': 7.2e-07, 'vol': 0.00044218, 'vol_cur': 574.90580265, 'last': 8.4e-07, 'buy': 6.1e-07, 'sell': 8.5e-07, 'updated': 1499483986}, 'gb_btc': {'high': 9.44e-06, 'low': 8e-06, 'avg': 8.72e-06, 'vol': 0.1228848, 'vol_cur': 14226.75275192, 'last': 8e-06, 'buy': 8e-06, 'sell': 9.22e-06, 'updated': 1499483932}, 'hvco_btc': {'high': 3e-06, 'low': 3e-06, 'avg': 3e-06, 'vol': 0.00059436, 'vol_cur': 198.12009314, 'last': 3e-06, 'buy': 2.26e-06, 'sell': 3.01e-06, 'updated': 1499484018}, 'incp_btc': {'high': 1.5e-06, 'low': 1.31e-06, 'avg': 1.4e-06, 'vol': 0.00258559, 'vol_cur': 1795.4114072, 'last': 1.31e-06, 'buy': 1.31e-06, 'sell': 1.54e-06, 'updated': 1499483988}, 'kubo_btc': {'high': 1e-08, 'low': 1e-08, 'avg': 1e-08, 'vol': 0.00033639, 'vol_cur': 33639.62075848, 'last': 1e-08, 'buy': 0, 'sell': 1e-08, 'updated': 1499484075}, 'star_btc': {'high': 2e-08, 'low': 1e-08, 'avg': 1e-08, 'vol': 0.02127209, 'vol_cur': 1703289.39887862, 'last': 2e-08, 'buy': 1e-08, 'sell': 2e-08, 'updated': 1499483992}, 'dbg_btc': {'high': 9e-07, 'low': 6.5e-07, 'avg': 7.7e-07, 'vol': 0.00037516, 'vol_cur': 506.04756084, 'last': 9e-07, 'buy': 6.6e-07, 'sell': 9e-07, 'updated': 1499484042}, 'flvr_btc': {'high': 9.7e-07, 'low': 9.6e-07, 'avg': 9.6e-07, 'vol': 0.00870545, 'vol_cur': 9025.01350299, 'last': 9.6e-07, 'buy': 9.6e-07, 'sell': 1.11e-06, 'updated': 1499483910}, 'mnm_btc': {'high': 9.8e-06, 'low': 9.75e-06, 'avg': 9.77e-06, 'vol': 0.00335631, 'vol_cur': 343.80917952, 'last': 9.75e-06, 'buy': 9.06e-06, 'sell': 9.84e-06, 'updated': 1499484040}, 'ree_btc': {'high': 1.846e-05, 'low': 5e-06, 'avg': 1.173e-05, 'vol': 1.31600115, 'vol_cur': 106066.73539796, 'last': 1.081e-05, 'buy': 1.053e-05, 'sell': 1.1e-05, 'updated': 1499483937}, 'tra_btc': {'high': 1.177e-05, 'low': 1.157e-05, 'avg': 1.167e-05, 'vol': 0.00227036, 'vol_cur': 194.15848477, 'last': 1.177e-05, 'buy': 1.081e-05, 'sell': 1.2e-05, 'updated': 1499483971}, 'btco_btc': {'high': 2e-08, 'low': 1e-08, 'avg': 1e-08, 'vol': 0.00410194, 'vol_cur': 390194.45908182, 'last': 1e-08, 'buy': 1e-08, 'sell': 2e-08, 'updated': 1499483992}, 'dbtc_btc': {'high': 6.9e-07, 'low': 6.4e-07, 'avg': 6.6e-07, 'vol': 0.02121267, 'vol_cur': 31520.14805242, 'last': 6.8e-07, 'buy': 6.8e-07, 'sell': 6.9e-07, 'updated': 1499483977}, 'exit_btc': {'high': 1e-08, 'low': 1e-08, 'avg': 1e-08, 'vol': 0.0014, 'vol_cur': 140000, 'last': 1e-08, 'buy': 0, 'sell': 1e-08, 'updated': 1499484026}, 'ecchi_btc': {'high': 4.8e-07, 'low': 3e-07, 'avg': 3.9e-07, 'vol': 0.31126073, 'vol_cur': 894910.26351769, 'last': 4.7e-07, 'buy': 3.4e-07, 'sell': 4.3e-07, 'updated': 1499483958}, 'bon_btc': {'high': 2e-08, 'low': 1e-08, 'avg': 1e-08, 'vol': 0.00789577, 'vol_cur': 511416.8795699, 'last': 1e-08, 'buy': 1e-08, 'sell': 2e-08, 'updated': 1499484052}, 'rio_btc': {'high': 1e-08, 'low': 1e-08, 'avg': 1e-08, 'vol': 0.00084959, 'vol_cur': 84959.98003992, 'last': 1e-08, 'buy': 0, 'sell': 1e-08, 'updated': 1499483897}, 'sp_btc': {'high': 2e-08, 'low': 1e-08, 'avg': 1e-08, 'vol': 0.00740505, 'vol_cur': 725008.57506723, 'last': 2e-08, 'buy': 1e-08, 'sell': 2e-08, 'updated': 1499484093}, 'sling_btc': {'high': 1.101e-05, 'low': 1.1e-05, 'avg': 1.1e-05, 'vol': 0.00984824, 'vol_cur': 894.9280408, 'last': 1.101e-05, 'buy': 1.102e-05, 'sell': 1.199e-05, 'updated': 1499484014}, 'talk_btc': {'high': 3.08e-06, 'low': 9.9e-07, 'avg': 2.03e-06, 'vol': 0.13893546, 'vol_cur': 68395.5287583, 'last': 9.9e-07, 'buy': 1.01e-06, 'sell': 2.56e-06, 'updated': 1499484022}, 'htc_btc': {'high': 2e-07, 'low': 5e-08, 'avg': 1.2e-07, 'vol': 23.37253717, 'vol_cur': 320981651.8312531, 'last': 1.6e-07, 'buy': 1.6e-07, 'sell': 1.8e-07, 'updated': 1499484092}}
                # {'success': 0, 'error': 'Empty pair list'}
                for key, value in result.items():
                    dict_ALL_COIN_DATA[key].setCurrentPrice(value['last'], value['buy'], value['sell'], value['updated'])


            except:
                print(self.coinList + ' : error')
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
                    bidPrice = buy_actual_price * LAST_SELL_PRICE_RATE
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

    #result = yobit.get_ticker_bulk('jnt_btc-omg_btc-onx_btc-greenf_btc-bitok_btc-xin_btc-netko_btc-tle_btc-may_btc-proc_btc-dea_btc-mvr_btc-dashs_btc-mental_btc-c2_btc-tide_btc-vec2_btc-cnnc_btc-alien_btc-ctic_btc-muu_btc-batl_btc-tap_btc-xps_btc-pupa_btc-party_btc-dux_btc-eva_btc-glo_btc-bab_btc-cks_btc-snm_btc-mco_btc-edr2_btc-hmq_btc-laz_btc-ele_btc-ebonus_btc-bts_btc-etc_btc-dlisk_btc-rise_btc-ping_btc-plbt_btc-waves_btc-lsk_btc-elc_btc-shrp_btc-tag_btc-profit_btc-kiss_btc-xnm_btc-slco_btc-max_btc-knc_btc-week_btc-rby_btc-tlosh_btc-420g_btc-des_btc-exp_btc-kr_btc-eth_btc-rocket_btc-socc_btc-europe_btc-lbtc_btc-acrn_btc-ocean_btc-hyperx_btc-solar_btc-udown_btc-alex_btc-in_btc-jane_btc-look_btc-bstar_btc-money_btc-arh_btc-coral_btc-icon_btc-nodc_btc-shorty_btc-xcre_btc-kurt_btc-vidz_btc')

    #print(result)

    result = yobit.get_markets()
    coinString = ''

    for idx, Market in enumerate(result['result']):
        coin = Market['MarketName']
        if '_btc' in coin and Market['IsActive']:
            if idx % 40 == 0:
                coinString = coin
            else:
                coinString = coinString + '-' + coin

            objCoin = Coin(coin)
            dict_ALL_COIN_DATA.update({coin:objCoin})
            print('%d : %s' % (idx, coin))
            if idx % 40 == 39:
                ThreadGetTiker(coinString).start()
                coinString = ''

    if len(result['result']) % 40 != 39 :
        ThreadGetTiker(coinString).start()

    ##datetime.datetime.fromtimestamp(server_time)
    while True:
        #print(str(dict_ALL_COIN_DATA['ltc_btc'].list_price[0][0]) +' : ' + str(dict_ALL_COIN_DATA['ltc_btc'].list_price[0][4]))
        #print(str(datetime.datetime.fromtimestamp(dict_ALL_COIN_DATA['ltc_btc'].list_price[0][4])))
        #print(dict_ALL_COIN_DATA['ltc_btc'].list_price[0][4])

        for key, value in dict_ALL_COIN_DATA.items():
            if value.IsInTrading:
                prev_time = value.list_price[3][0]
                curr_time = value.list_price[4][0]
                prev_price_ask = value.list_price[3][2]
                curr_price_ask = value.list_price[4][2]


                price_gap_rate_ask = (curr_price_ask - prev_price_ask) / prev_price_ask
                printt('%s is in Trading : [%s : %.8f]->[%s:%.8f] : %.8f' % (key, str(datetime.datetime.fromtimestamp(prev_time)),prev_price_ask,str(datetime.datetime.fromtimestamp(curr_time)),curr_price_ask, price_gap_rate_ask))

        time.sleep(2)

if __name__  == "__main__":
    main()
