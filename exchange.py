from bittrex import Bittrex
from yobit import Yobit
import json

"""
Example:

from exchange import Exchange

myExchange = Exchange('yobit').getExchange()
markets = myExchange.get_markets()
"""


class Exchange:
    'Super Class'
    def __init__(self, exchange_name):
        self.exchange = exchange_name

    def getExchange(self):
        if self.exchange == 'bittrex':
            with open("secrets.json") as secrets_file:
                secrets = json.load(secrets_file)
                secrets_file.close()
                bittrex = Bittrex(secrets['key'], secrets['secret'])
                return bittrex
        elif self.exchange == 'yobit':
            with open("secrets_yobit.json") as secrets_file:
                secrets = json.load(secrets_file)
                secrets_file.close()
                yobit = Yobit(secrets['key'], secrets['secret'])
                return yobit






