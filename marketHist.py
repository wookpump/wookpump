import time
from bittrex import Bittrex
import json
import threading
from threading import Thread
import traceback
from pymongo import MongoClient


with open("secrets.json") as secrets_file:
    secrets = json.load(secrets_file)
    secrets_file.close()
    bittrex = Bittrex(secrets['key'], secrets['secret'])

client = MongoClient("mongodb://127.0.0.1:27017")
db = client.market_history

class ThreadGetMarketHistory(Thread):
    def __init__(self, MarketName):
        self.MarketName = MarketName
        threading.Thread.__init__(self)

    def run(self):
        while True:
            try:
                history = bittrex.get_market_history(self.MarketName, 2)
                result = db[MarketName].insert_one(history['result'][0])
                print(result)

            except:
                print(self.MarketName + ' : error')
                traceback.print_exc()
                break

            # time.sleep(1)

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

result = bittrex.get_markets()

for coin in result['result']:
    MarketName = coin['MarketName']
    if 'BTC-' in MarketName and coin['IsActive'] and isExcludedCoin(MarketName) is not True:
        try:
            ThreadGetMarketHistory(MarketName).start()
        except:
            print('error : ' + MarketName)
            # print(MarketName + ' : ' + str(currency))

