# twisted imports
from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor, protocol
from twisted.python import log
import json

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
        # not sure about the type for this yet
        self.order_history = []
        self.open_orders = []
        self.order_count = 0
        self.market_open = False
        self.flagged = True
        self.last_cancel = time.time()
        self.cancel_time = 5

    def connectionMade(self):
        # maybe do something here
        print("Connected.")
        # now do the hello handshake
        self.message({"type": "hello", "team": "STRAWBERRYRR"})

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
        pass

    def on_rejection(self, data):
        for x in open_orders:
            if x["id"] == data["order_id"]:
                open_orders.remove(x)
                break
    def on_order_filled(self, data):
        for x in open_orders:
            if x["order_id"] == data["order_id"]:
                open_orders.remove(x)
                if x["dir"] == "SELL":
                    self.positions[x["symbol"]] -= x["size"]
                    self.cash += x["size"] * x["price"]
                elif x["dir"] == "BUY": 
                    self.positions[x["symbol"]] += x["size"]
                    self.cash -= x["size"] * x["price"]
        print self.cash
        for symbol, position in self.positions.items():
            print("SYM: {0} POS: {1}".format(symbol, position))

    def on_out(self, data):
        pass

    def on_public_trade(self, data):
        """
        Handle a public trade on the market
        """
        pass

    def cancel_all(self): 
        for x in open_orders:
            cancel_order = {"type": "cancel", "order_id": x["id"]}
            self.message(cancel_order)
            open_orders.remove(x)

    def on_book_status(self, data):
        """
        Handle more current information about the book
        Make offers depending on the spread price of the book
        """

        if time.time() - self.last_cancel > self.cancel_time:
            self.cancel_all()
            self.last_cancel = time.time()

        symbol = data["symbol"]
        buy = data["buy"][0][0]
        sell = data["sell"][0][0]


        if (sell - buy > 2):
            buy += 1
            sell -= 1

        #place new orders
        order_amt = 1

        buy_order = {"type":"add", "order_id" : self.order_count, "symbol" : symbol, "dir" : "BUY", "price" : buy, "size" : order_amt}
        self.message(buy_order)
        self.open_orders.append(buy_order)
        self.order_count += 1


        sell_order = {"type":"add", "order_id" : self.order_count, "symbol" : symbol, "dir" : "SELL", "price" : sell, "size" : order_amt}
        self.message(sell_order)
        self.open_orders.append(sell_order)
        self.order_count += 1

        

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
