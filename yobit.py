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
        self.trade = ['ActiveOrders', 'getInfo', 'Trade', 'CancelOrder', 'ActiveOrders','GetDepositAddress']

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

        #{'ltc_btc': {'high': 0.02149593, 'low': 0.019, 'avg': 0.02024796, 'vol': 66.6218802, 'vol_cur': 3254.49119283, 'last': 0.02067049, 'buy': 0.02039001, 'sell': 0.02067012, 'updated': 1499253136}}
        #{'success': True, 'message': '', 'result': {'Bid': 0.02034974, 'Ask': 0.02037084, 'Last': 0.0203508}}

        if result[market]:
            result = {'success' : True, 'message' :'', 'result':{'Bid':result[market]['buy'], 'Ask':result[market]['sell'], 'Last':result[market]['last']}}
        else:
            result = {'success': False, 'message': result['error'], 'result': None}

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

        result = self.api_query('CancelOrder', {'order_id': uuid})
        return result

    def get_open_orders(self, market):
        """
        Get all orders that you currently have opened. A specific market can be requested
        /market/getopenorders
        :param market: String literal for the market (ie. BTC-LTC)
        :type market: str
        :return: Open orders info in JSON
        :rtype : dict
        """
        #{'success': True, 'message': '', 'result': [{'Uuid': None, 'OrderUuid': '7f43f22f-586b-46d8-a4b2-f457cfeb2aac', 'Exchange': 'BTC-GEO', 'OrderType': 'LIMIT_SELL', 'Quantity': 2.03478908, 'QuantityRemaining': 2.03478908, 'Limit': 0.00097503, 'CommissionPaid': 0.0, 'Price': 0.0, 'PricePerUnit': None, 'Opened': '2017-07-03T14:13:20.903', 'Closed': None, 'CancelInitiated': False, 'ImmediateOrCancel': False, 'IsConditional': False, 'Condition': 'NONE', 'ConditionTarget': None}]}
        #{'success': 1, 'return': {'240005185729406': {'pair': 'lsk_btc', 'type': 'sell', 'amount': 1, 'rate': 0.096319, 'timestamp_created': '1499255345', 'status': 0}}}
        result = self.api_query('ActiveOrders', {'pair': market})

        openOrder =[]
        if result['success'] == 1:
            for key, value in result['return'].items():
                openOrder.append({'OrderUuid':key})
            result = {'success': True, 'message': '', 'result' : openOrder}
        else:
            result = {'success': False, 'message': '', 'result': openOrder}

        return result

    def get_balance(self, currency):
        """
        Used to retrieve the balance from your account for a specific currency
        /account/getbalance
        :param currency: String literal for the currency (ex: LTC)
        :type currency: str
        :return: Balance info in JSON
        :rtype : dict
        """

        result = self.api_query('getInfo', {'coinName': currency, 'need_new':0})

        #{'success': True, 'message': '', 'result': {'Currency': 'NXS', 'Balance': 1.55257461, 'Available': 1.55257461, 'Pending': 0.0, 'CryptoAddress': None}}
        #{'success': 1, 'return': {'rights': {'info': 1, 'trade': 1, 'deposit': 1, 'withdraw': 0}, 'funds': {'btc': 0.00705219, 'lsk': 2}, 'funds_incl_orders': {'btc': 0.00705219, 'lsk': 2}, 'transaction_count': 0, 'open_orders': 0, 'server_time': 1499255221}}
        #{'success': 1, 'return': {'rights': {'info': 1, 'trade': 1, 'deposit': 1, 'withdraw': 0}, 'funds': {'btc': 0.00705219, 'lsk': 1}, 'funds_incl_orders': {'btc': 0.00705219, 'lsk': 2}, 'transaction_count': 0, 'open_orders': 0, 'server_time': 1499255362}}

        #{'success': False, 'message': 'INVALID_CURRENCY', 'result': None}
        #{'success': 1, 'return': {'rights': {'info': 1, 'trade': 1, 'deposit': 1, 'withdraw': 0}, 'funds': {'btc': 0.00705219, 'lsk': 1}, 'funds_incl_orders': {'btc': 0.00705219, 'lsk': 2}, 'transaction_count': 0, 'open_orders': 0, 'server_time': 1499255600}}
        try:
            result = {'success': True, 'message' :'', 'result':{'Currency': currency, 'Balance': result['return']['funds_incl_orders'][currency], 'Available': result['return']['funds'][currency], 'Pending': 0.0, 'CryptoAddress': None}}
        except:
            result = {'success': False, 'message' :'', 'result':{'Currency': currency, 'Balance': 0.0, 'Available': 0.0, 'Pending': 0.0, 'CryptoAddress': None}}
        return result

    def get_markets(self):
        """
        Used to get the open and available trading markets
        at Bittrex along with other meta data.
        :return: Available market info in JSON
        :rtype : dict
        """

        #

        result = self.api_query('info')
        print(str(result))
        detail = []
        for key, value in result['pairs'].items():
            IsActive = False
            if value['hidden'] ==0:
                IsActive = True
            dict_result = {'MarketCurrency':key.split('_')[0],'BaseCurrency': key.split('_')[1], 'MarketName':key,'IsActive':IsActive}
            detail.append(dict_result)

        result={'success' : True, 'message':'', 'result':detail}
        return result