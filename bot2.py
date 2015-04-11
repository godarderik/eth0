# twisted imports
from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor, protocol
from twisted.python import log
import json
import pickle
import csv
import math

# system imports
import time, sys

TEST_PUBLIC_IP = "52.1.34.5"
TEST_PRIVATE_IP = "10.0.138.127"

JSON_PORT = 25000
SLOW_MARKET = 0
FAST_MARKET = 1
EMPTY_MARKET = 2

class MarketBot(Protocol):
    def __init__(self):
        """
        Set up the data for later
        """
        self.cash = 0
        self.positions = {
            'FOO': 0,
            'BAR': 0,
            'BAZ': 0,
            'QUUX': 0,
            'CORGE': 0,
        }

        self.values = {
            'FOO': 0,
            'BAR': 0,
            'BAZ': 0,
            'QUUX': 0,
            'CORGE': 0,
        }
        self.sigmas = {
            'FOO': 0,
            'BAR': 0,
            'BAZ': 0,
            'QUUX': 0,
            'CORGE': 0,
        }

        self.spread = {
            'FOO': [-99999999999,99999999999],
            'BAR': [-99999999999,99999999999],
            'BAZ': [-99999999999,99999999999],
            'QUUX': [-99999999999,99999999999],
            'CORGE': [-99999999999,99999999999],
        }
        # not sure about the type for this yet
        self.order_history = []
        self.open_orders = []

        self.corge_book = {}
        self.foo_book = {}
        self.bar_book = {}

        self.converts = []
        self.convert_amount = 0 
        self.convert_prices = {}

        self.order_count = 0
        self.market_open = False
        self.flagged = True
        self.last_cancel = time.time()
        self.cancel_time = 1
        self.canceling = False
        self.file = open('data.csv', 'w')
        self.csv = csv.writer(self.file)
        self.orders = {}

    def connectionMade(self):
        # maybe do something here
        print("Connected.")
        # now do the hello handshake
        self.message({"type": "hello", "team": "STRAWBERRY"})

    def connectionLost(self, reason):
        print("Disconnected for reason: {0}".format(reason))

    def dataReceived(self, data):
        """
        Do something with the data
        """
        for datum in data.split('\n')[:-1]:
            try:
                self.handle_single_message(json.loads(datum.strip()))
            except:            
                pass
    
    def handle_single_message(self, data):
        """
        handle a single message
        """

        # publicly exchanged information
        if data['type'] == 'trade':
            self.on_public_trade(data)
        elif data['type'] == 'book':
            self.on_book_status(data)

        # handle our own order information
        elif data['type'] == 'ack':
            self.on_acknowledge(data)
        elif data['type'] == 'reject':
            self.on_rejection(data)
        elif data['type'] == 'fill':
            self.on_order_filled(data)
        elif data['type'] == 'out':
            self.on_out(data)

        # boilerplate stuff
        elif data['type'] == 'hello':
            self.on_hello(data)
        elif data['type'] == 'market_open':
            self.on_market_open(data)
        elif data['type'] == 'error':
            self.on_error(data)

    def on_acknowledge(self, data):
        if (data['order_id'] in self.converts):
            #sell off the reults of our converts
            sell_order_foo = {"type":"add", "order_id" : data["order_id"], symbol:"FOO", "dir" : "SELL", "price" : self.convert_prices["foo"], "size" : int(.3 * self.convert_amount)}
            sell_order_bar = {"type":"add", "order_id" : data["order_id"], symbol:"BAR", "dir" : "SELL", "price" : self.convert_prices["bar"], "size" : int(.8 * self.convert_amount)}
            self.message(sell_order_foo)
            self.message(sell_order_bar)
            self.converts.remove(data['order_id'])

        else: 
            order = self.orders[data['order_id']]
            self.open_orders.append(order)
            # update the spread
            if order['symbol'] == 'BAZ':
                self.csv.writerow([order['price']])

            if order['dir'] == 'BUY':
                self.spread[order['symbol']][0] = order['price']
            elif order['dir'] == 'SELL':
                self.spread[order['symbol']][1] = order['price']

    def on_rejection(self, data):
        print("REJECTED!! reason: {0}".format(data['reason']))
        print("\n" * 10)
        pass

    def on_order_filled(self, data):
        if self.flagged:
            self.flagged = False
            print("ORDER FILLED : {0}".format(data['order_id']))
            print self.cash
            # for symbol, position in self.positions.items():
            #     print("SYM: {0} POS: {1}".format(symbol, position))
            print(len(self.open_orders))
            print(data)
        for x in self.open_orders:
            if x["order_id"] == data["order_id"]:
                self.open_orders.remove(x)
                if x["dir"] == "SELL":
                    self.positions[x["symbol"]] -= x["size"]
                    self.cash += x["size"] * x["price"]
                    break
                elif x["dir"] == "BUY": 
                    self.positions[x["symbol"]] += x["size"]
                    self.cash -= x["size"] * x["price"]
                    break
        # print self.cash
        self.calculate_overall_position()
        # for symbol, position in self.positions.items():
        #     print("SYM: {0} POS: {1}".format(symbol, position))
    

    def on_out(self, data):
        pass

    def on_public_trade(self, data):
        """
        Handle a public trade on the market
        """
        self.values[data['symbol']] = data['price']

    def cancel_all(self):
        # for x in self.open_orders: 
        print("calling cancel all")
        print("\n"*10)
        for x in self.open_orders:
            print("canceling order: {0}".format(x['order_id']))
            print("total orders: {0}".format(len(self.open_orders))) 
            cancel_msg = {"type": "cancel", "order_id": x["order_id"]}
            self.message(cancel_msg)
        self.open_orders = []
        self.spread = {
            'FOO': [-99999999999,99999999999],
            'BAR': [-99999999999,99999999999],
            'BAZ': [-99999999999,99999999999],
            'QUUX': [-99999999999,99999999999],
            'CORGE': [-99999999999,99999999999],
        }


    def etf_artbitrage(self,data):

        if self.corge_book != {} and self.foo_book != {} and self.bar_book != {}:
            print "here"
            self.corge_buy_price = self.corge_book["buy"][0][0]
            self.corge_sell_price = self.corge_book["sell"][0][0]

            self.foo_buy_price = self.foo_book["buy"][0][0]
            self.foo_sell_price = self.foo_book["sell"][0][0]

            self.foo_buy_price = self.foo_book["buy"][0][0]
            self.foo_sell_price = self.foo_book["sell"][0][0]

            buy_etf_diff = .3 * foo_sell_price + .8 * bar_sell_price - corge_buy_price - 100
            sell_etf_diff = corge_sell_price - .3 * foo_sell_price - .8 * bar_sell_price - 100
            if buy_etf_diff > 0: 
                self.convert_amount = corge_book["buy"][0][1] - corge_book["buy"][0][1]%10 #must be multiple of 10 
                self.converts.append(self.order_count)
                convert_msg = {"type": "convert", "order_id": data["order_id"], "symbol": "CORGE", "dir": "BUY", "size": self.convert_amount}
                self.message(convert_msg)
                self.order_count += 1
                self.convert_prices["foo"] = foo_sell_price
                self.convert_prices["bar"] = foo_bar_price

            elif sell_etf_diff > 0: 
                #sell etf and convert
                pass




    def on_book_status(self, data):
        """
        Handle more current information about the book
        Make offers depending on the spread price of the book
        """

        print("Open orders: {0}".format(len(self.open_orders)))

        if len(self.open_orders) == 0:
            self.canceling = False

        if self.canceling:
            print("CANCELING - still")
            return

        if time.time() - self.last_cancel > self.cancel_time:
            self.canceling = True   
            self.cancel_all()
            self.last_cancel = time.time()
            print("CANCELING")
            return


        symbol = data["symbol"]
        print symbol
        if symbol == "CORGE": 
            self.corge_book = data
        elif symbol == "FOO":
            self.foo_book = data
        elif symbol == "BAR":
            self.bar_book = data

        self.etf_artbitrage()
        '''
        buy = data["buy"][0][0]
        sell = data["sell"][0][0]

        if (sell - buy > 2):
            buy += 1
            sell -= 1
        else:
            return

        if (self.spread[symbol][0] > buy):
            return 

        if (self.spread[symbol][1] < sell):
            return 
            
        #place new orders
        buy_order_amt = int(math.floor(100*(sell-buy)/50*math.e**(-1*self.positions[symbol]/100)))

        buy_order = {"type":"add", "order_id" : self.order_count, "symbol" : symbol, "dir" : "BUY", "price" : buy, "size" : buy_order_amt}
        self.message(buy_order)
        self.order_count += 1

        sell_order_amt = 50 - sell_order_amt
        if sell_order_amt < 0: 
            sell_order_amt = 0

        sell_order = {"type":"add", "order_id" : self.order_count, "symbol" : symbol, "dir" : "SELL", "price" : sell, "size" : sell_order_amt}
        self.message(sell_order)
        self.order_count += 1   

        self.orders[buy_order['order_id']] = buy_order  
        self.orders[sell_order['order_id']] = sell_order  
        '''

    def calculate_overall_position(self):
        overall = self.cash
        for symbol, position in self.positions.items():
            overall += self.values[symbol] * position 
        # print(overall)
        # self.csv.writerow([overall])
        return overall

    def on_hello(self, data):
        """
        Handle the hello handshake response
        """
        self.cash = data['cash']
        self.market_open = data['market_open']
        for position in data['symbols']:
            self.positions[position['symbol']] = position['position']
        print("connected to exchange\nCash: {0}".format(self.cash))
        for symbol, position in self.positions.items():
            print("SYM: {0} POS: {1}".format(symbol, position))

    def on_market_open(self, data):
        self.market_open = data['open']
        """
        Do we need to do more?
        """

    def on_error(self, data):
        """
        Do stuff
        """
        print(data)

    def message(self, message):
        self.transport.write(json.dumps(message) + '\n')

class MarketBotFactory(protocol.ClientFactory):
    """
    A factory for MarketBots.

    A new protocol instance will be created each time we connect to the server.
    """

    def __init__(self):
        """
        Do something clever here
        """
        pass

    def buildProtocol(self, addr):
        p = MarketBot()
        p.factory = self
        return p

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason
        reactor.stop()

if __name__ == '__main__':
    # initialize logging
    log.startLogging(sys.stdout)
    
    # create factory protocol and application
    f = MarketBotFactory()

    # connect factory to this host and port
    reactor.connectTCP(TEST_PRIVATE_IP, JSON_PORT + SLOW_MARKET, f)

    # run bot
    reactor.run()