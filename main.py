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
        # not sure about the type for this yet
        self.order_history = []
        self.market_open = False
        self.flagged = True

    def connectionMade(self):
        # maybe do something here
        print("Connected.")
        # now do the hello handshake
        self.message(json.dumps({"type": "hello", "team": "STRAWBERRY"}))

    def connectionLost(self, reason):
        print("Disconnected for reason: {0}".format(reason))

    def dataReceived(self, data):
        """
        Do something with the data
        """
        if (self.flagged):
            print(data)
            print(dir(data))
            self.flagged = False
        return
        message_data = json.loads(data)

        # publicly exchanged information
        if message_data['type'] == 'trade':
            self.on_public_trade(message_data)
        elif message_data['type'] == 'book':
            self.on_book_status(message_data)

        # handle our own order information
        elif message_data['type'] == 'ack':
            self.on_acknowledge(message_data)
        elif message_data['type'] == 'reject':
            self.on_rejection(message_data)
        elif message_data['type'] == 'fill':
            self.on_order_filled(message_data)
        elif message_data['type'] == 'out':
            self.on_out(message_data) 

        # boilerplate stuff
        elif message_data['type'] == 'hello':
            self.on_hello(message_data)
        elif message_data['type'] == 'market_open':
            self.on_market_open(message_data)
        elif message_data['type'] == 'error':
            self.on_error(message_data)

    def on_acknowledge(self, data):
        """
        
        """
        pass

    def on_rejection(self, data):
        """
        Cry
        """
        pass

    def on_order_filled(self, data):
        """

        """
        pass

    def on_out(self, data):
        """

        """
        pass

    def on_public_trade(self, data):
        """
        Handle a public trade on the market
        """
        pass

    def on_book_status(self, data):
        """
        Handle more current information about the book
        """
        pass

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
        self.transport.write(message + '\n')

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
