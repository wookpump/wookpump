"""
   See https://bittrex.com/Home/Api
"""

import time
import hmac
import hashlib
try:
    from urllib import urlencode
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urlencode
    from urllib.parse import urljoin
import requests
import json

class Yobit(object):

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret
        self.public = ['info', 'ticker', 'depth', 'trades']
        self.trade = ['ActiveOrders', 'getInfo', 'Trade']

    def api_query(self, method, values={}):
        if method in self.public:
            #https://yobit.net/api/3/ticker/ltc_btc
            url = 'https://yobit.net/api/3/' + method
            for i, k in values.items():
                url += '/' + k.lower()

            req = requests.get(url)
            #return json.loads(req.text)
            return req.json()

        elif method in self.trade:
            url = 'https://yobit.net/tapi'
            values['method'] = method
            values['nonce'] = str(int(time.time()))
            body =  urlencode(values)
            #headers={"apisign": hmac.new(self.api_secret.encode(), request_url.encode(), hashlib.sha512).hexdigest()}
            #POST-parameters (?param0=val0 & ...& nonce=1) signed by secret key through HMAC-SHA512
            signature = hmac.new(self.secret.encode(), body.encode(), hashlib.sha512).hexdigest()
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Key': self.key,
                'Sign': signature
            }

            req = requests.post(url, data=values, headers=headers)
            return req.json()

        return False
    
    def get_ticker(self, market):

        result = self.api_query('ticker', {'market': market})

        for key, value in result.items():
            if market == key:
                result = {'success' : True, 'message' :'', 'result':{'Bid':value['buy'], 'Ask':value['sell'], 'Last':value['last']}}
                break
            else:
                result = {'success': False, 'message': result['error'], 'result': None}
                break
        return result


    def activeorders(self, market):
        return self.api_query('ActiveOrders', {'pair': market})

    def getinfo(self):
        return self.api_query('getInfo')


    def buy_limit(self, market, quantity, rate):
        """
        Used to place a buy order in a specific market. Use buylimit to place
        limit orders Make sure you have the proper permissions set on your
        API keys for this call to work
        /market/buylimit
        :param market: String literal for the market (ex: BTC-LTC)
        :type market: str
        :param quantity: The amount to purchase
        :type quantity: float
        :param rate: The rate at which to place the order.
            This is not needed for market orders
        :type rate: float
        :return:
        :rtype : dict
        """
        return self.api_query('Trade', {'type':'buy', 'pair': market, 'amount': quantity, 'rate':rate})

    def sell_limit(self, market, quantity, rate):
        """
        Used to place a sell order in a specific market. Use selllimit to place
        limit orders Make sure you have the proper permissions set on your
        API keys for this call to work
        /market/selllimit
        :param market: String literal for the market (ex: BTC-LTC)
        :type market: str
        :param quantity: The amount to purchase
        :type quantity: float
        :param rate: The rate at which to place the order.
            This is not needed for market orders
        :type rate: float
        :return:
        :rtype : dict
        """
        return self.api_query('Trade', {'type':'sell', 'pair': market, 'amount': quantity, 'rate':rate})

    def cancel(self, uuid):
        """
        Used to cancel a buy or sell order
        /market/cancel
        :param uuid: uuid of buy or sell order
        :type uuid: str
        :return:
        :rtype : dict
        """
        return self.api_query('CancelOrder', {'order_id': uuid})

    def get_open_orders(self, market):
        """
        Get all orders that you currently have opened. A specific market can be requested
        /market/getopenorders
        :param market: String literal for the market (ie. BTC-LTC)
        :type market: str
        :return: Open orders info in JSON
        :rtype : dict
        """
        return self.api_query('ActiveOrders', {'pair': market})

    def get_balance(self, currency):
        """
        Used to retrieve the balance from your account for a specific currency
        /account/getbalance
        :param currency: String literal for the currency (ex: LTC)
        :type currency: str
        :return: Balance info in JSON
        :rtype : dict
        """
        return self.api_query('GetDepositAddress', {'coinName': currency, 'need_new':0})