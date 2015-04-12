# twisted imports
from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor, protocol
from twisted.python import log
from twisted.internet.defer import setDebugging
import json
import pickle
import csv

setDebugging(True)
# system imports
import time, sys

TEST_PUBLIC_IP = "52.1.34.5"
TEST_PRIVATE_IP = "10.0.138.127"

LOCAL_FORWARD_IP = "localhost"

JSON_PORT = 25000
SLOW_MARKET = 0
FAST_MARKET = 1
EMPTY_MARKET = 2

ALPHA_FACTOR = 1.0
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

        self.order_positions = {
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
        self.cancel_time = 5
        self.canceling = False
        self.file = open('data.csv', 'w')
        self.csv = csv.writer(self.file)
        self.orders = {}

    def connectionMade(self):
        # maybe do something here
        print("Connected.")
        # now do the hello handshake
        self.message({"type": "hello", "team": "A"})

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

    def cancel_all_buy_symbol(self, symbol):
        print("SYM: {0} canceling buy orders {1}".format(symbol, self.positions[symbol]))

        for order in filter(lambda x: x['symbol'] == symbol and x['dir'] == 'BUY', self.open_orders):
            print(order['symbol'])
            cancel_msg = {"type": "cancel", "order_id": order["order_id"]}
            self.message(cancel_msg)

    def cancel_all_sell_symbol(self, symbol):
        print("SYM: {0} canceling sell orders {1}".format(symbol, self.positions[symbol]))

        for order in filter(lambda x    : x['symbol'] == symbol and x['dir'] == "SELL", self.open_orders):
            print(order['symbol'])
            cancel_msg = {"type": "cancel", "order_id": order["order_id"]}
            self.message(cancel_msg)

    def on_order_filled(self, data):
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

        symbol = data['symbol']
        if self.positions[symbol] > 200:
            self.cancel_all_buy_symbol(symbol)
        
        if self.positions[symbol] < -200:
            self.cancel_all_sell_symbol(symbol)

        self.calculate_overall_position()    

    def on_out(self, data):
        pass

    def on_public_trade(self, data):
        """
        Handle a public trade on the market
        """
        self.values[data['symbol']] = data['price']

    def cancel_all(self):
        # for x in self.open_orders: 
        self.last_cancel = time.time()
        print("calling cancel all")

        for symbol, position in self.positions.items():
            print("SYM: {0}|POS: {1}".format(symbol, position))

        for x in self.open_orders:
            #print("canceling order: {0}".format(x['order_id']))
            #print("total orders: {0}".format(len(self.open_orders))) 
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

    def on_book_status(self, data):
        """
        Handle more current infor mation about the book
        Make offers depending on the spread price of the book
        """

        if len(self.open_orders) == 0:
            self.canceling = False

        if self.canceling:
            print("CANCELING - still - {0}".format(len(self.open_orders)))
            self.cancel_all()
            return

        if time.time() - self.last_cancel > self.cancel_time:
            self.canceling = True
            self.cancel_all()
            print("CANCELING")
            return

        symbol = data["symbol"]
        buy = data["buy"][0][0]
        sell = data["sell"][0][0]

        if (sell - buy > 2):
            buy += 1
            sell -= 1
        else:
            print("not enough margin {0}".format(sell - buy))
            return

        # figure out if we should buy or sell or not
        should_buy = True
        should_sell = True

        # make sure we don't shoot ourselves
        if (self.spread[symbol][0] > buy):
            should_buy = False 

        if (self.spread[symbol][1] < sell):
            should_sell = False

        # should we buy at all? based on our position
        if self.positions[symbol] > 200:
            should_buy = False
            self.cancel_all_buy_symbol(symbol)
        
        if self.positions[symbol] < -200:
            should_sell = False
            self.cancel_all_sell_symbol(symbol)

        #place new orders
        order_amt = ORDER_AMOUNT

        if not (should_buy or should_sell):
            print("neither buying or selling...")
            return

        if should_buy:
            buy_order = {
                "type": "add", 
                "order_id" : self.order_count, 
                "symbol" : symbol, 
                "dir" : "BUY", 
                "price" : buy, 
                "size" : order_amt
            }
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
        print("PNL {0}".format(overall))
        self.csv.writerow([overall])
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
    reactor.connectTCP(LOCAL_FORWARD_IP, 8888, f)

    # run bot
    reactor.run()
