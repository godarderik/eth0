"""
The smart ideas ported over to production
"""
# twisted imports
from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor, protocol
from twisted.python import log
import json
import pickle
import csv

# system imports
import time, sys

TEST_PUBLIC_IP = "52.1.34.5"
TEST_PRIVATE_IP = "10.0.138.127"
PRODUCTION_IP = "localhost"

LOCAL_FORWARD_IP = "localhost"

JSON_PORT = 25000
SLOW_MARKET = 0
FAST_MARKET = 1
EMPTY_MARKET = 2

ORDER_AMOUNT = 1

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
        self.message({"type": "hello", "team": "STRAWBERRYBLUE"})

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
        messages = []
        for x in self.open_orders:
            self.message({"type": "cancel", "order_id": x["order_id"]})
        self.open_orders = []
        self.spread = {
            'FOO': [-99999999999,99999999999],
            'BAR': [-99999999999,99999999999],
            'BAZ': [-99999999999,99999999999],
            'QUUX': [-99999999999,99999999999],
            'CORGE': [-99999999999,99999999999],
        }

    def on_book_status(self, data):
        """
        Handle more current information about the book
        Make offers depending on the spread price of the book
        """
        if len(self.open_orders) == 0:
            self.canceling = False

        if time.time() - self.last_cancel > self.cancel_time:
            print("CANCELING")
            self.canceling = True   
            self.last_cancel = time.time()
            self.cancel_all()
            return

        if self.canceling:
            if self.last_cancel - time.time() > 5:
                print("it's been long enough, wiping")
                self.open_orders = [] # forget about the orders
                self.canceling = False
            print("CANCELING - still - {0}".format(len(self.open_orders)))
            return


        symbol = data["symbol"]
        buy = data["buy"][0][0]
        sell = data["sell"][0][0]

        should_buy = True
        should_sell = True

        if (sell - buy > 2):
            buy += 1
            sell -= 1
        else:
            return

        # don't penny ourselves
        if (self.spread[symbol][0] > buy):
            should_buy = False

        if (self.spread[symbol][1] < sell):
            should_sell = False

        #place new orders
        order_amt = ORDER_AMOUNT

        if should_buy:
            buy_order = {"type":"add", "order_id" : self.order_count, "symbol" : symbol, "dir" : "BUY", "price" : buy, "size" : order_amt}
            self.message(buy_order)
            self.order_count += 1
            self.orders[buy_order['order_id']] = buy_order  

        if should_sell:
            sell_order = {"type":"add", "order_id" : self.order_count, "symbol" : symbol, "dir" : "SELL", "price" : sell, "size" : order_amt}
            self.message(sell_order)
            self.order_count += 1   
            self.orders[sell_order['order_id']] = sell_order  


    def calculate_overall_position(self):
        overall = self.cash
        for symbol, position in self.positions.items():
            overall += self.values[symbol] * position 
        print("PNL: {0}".format(overall))
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

    def message_multiple(self, messages):
        self.transport.write('\n'.join([json.dumps(message) for message in messages]) + '\n')

    def message(self, message):
        self.transport.write(json.dumps(message) + '\n')

class MarketBotFactory(protocol.ClientFactory):
    """
    A factory for MarketBots.

    A new protocol instance will be created each time we connect to the server.
    """

    def __init__(self, drop=False):
        """
        Do something clever here
        """
        self.drop = drop
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
    
    if len(sys.argv) > 1:
        drop = True
    else:
        drop = False

    if drop:
        print("DROPPING...\n\n\n\n")

    # create factory protocol and application
    f = MarketBotFactory(drop=drop)

    # connect factory to this host and port
    reactor.connectTCP(LOCAL_FORWARD_IP, 8888, f)

    # run bot
    reactor.run()
