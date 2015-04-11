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

    def connectionMade(self):
        # maybe do something here
        print("Connected.")
        # now do the hello handshake
        self.message({"type": "hello", "team": "strawberry"})

    def connectionLost(self, reason):
        print("Disconnected for reason: {0}".format(reason))

    def dataReceived(self, data):
        """
        Do something with the data
        """
        message_data = json.loads(data)
        if message_data['type'] == 'hello':
            self.onHello(message_data)

    def onHello(self, data):
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
    reactor.connectTCP(TEST_PUBLIC_IP, JSON_PORT + SLOW_MARKET, f)

    # run bot
    reactor.run()