#!/usr/bin/env python

import yaml
import time
import socket
import select
import logging
import threading
logging.basicConfig(level=logging.DEBUG, format='[%(threadName)-10s] %(message)s')
class probe(object):
    '''This class consists of two parts: a listening part that holds
    open a number of sockets, and a connector that connects to those sockets

    The idea is to measure connectivity between two or more networks, and report that
    to graphite
    '''
    #pylint: disable=too-many-instance-attributes
    def __init__(self, configFile = 'config.yml'):
        '''ENGAGE
        '''
        self.configFile     = configFile
        self.portList       = []
        self.hostList       = []
        self.running        = True
        self.graphiteHost   = ''
        self.graphitePrefix = ''
        self.graphitePort   = 2003
        self.threads        = []
        self.cycleTime      = 60 # seconds
        self.timeout        = 0.5 # connection timeout in seconds
        self.metrics        = []
        self.hostname       = socket.gethostname()

    def readConfig(self):
        '''Reads the yaml file in configFile and populates the
        probe and port list
        '''
        with open(self.configFile) as configFile:
            try:
                config = yaml.load(configFile)
            except Exception, e:
                logging.error("Unable to open config file: {0}".format(e))

            try:
                self.portList       = config['ports']
                self.hostList       = config['hosts']
                self.graphiteHost   = config['graphitehost']
                self.graphitePrefix = config['graphiteprefix']
                self.cycleTime      = config['cycletime']
                if 'hostname' in config:
                    self.hostname   = config['hostname']
            except Exception, e:
                logging.error("Error in config file: {0}\n\tThis is possibly a typo".format(e))

            return {'portlist': self.portList, 'hostlist': self.hostList, 'graphiteHost': self.graphiteHost, 'graphitePrefix': self.graphitePrefix, 'hostname': self.hostname}

    def listenPort(self, port):
        '''Opens a single port and listens for connections.

        will return PONG if it recieves PING, otherwise it'll return FAILURE

        Closes connection after every message
        '''
        logging.debug('creating listening port')
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(('0.0.0.0', port))
        except Exception, e:
            logging.error('failed to bind to port: {0}'.format(e))
            return False
        sock.listen(10)
        socketList = []
        socketList.append(sock)
        while self.running:
            readSocket, _, _, =select.select(socketList,[],[])
            logging.debug('New socket/connection')
            for incoming in readSocket:
                if incoming == sock:
                    try:
                        #then we need to accept the connection:
                        connection, address = sock.accept()
                        logging.debug('I have a connection from: {0}'.format(address))
                        socketList.append(connection)
                    except Exception, e:
                        logging.error('Error accepting connection: {0}'.format(e))
                else:
                    #Connection die all the time...
                    try:
                        message = incoming.recv(1024)
                        failure = False
                    except Exception, e:
                        logging.error('Cannot read from connection: {0}'.format(e))
                        incoming.close()
                        socketList.remove(connection)
                        failure = True
                    if not failure:
                        logging.debug("message from {0}: {1}".format(incoming.getpeername()[0], message))
                        if message.rstrip() == 'PING':
                            try:
                                incoming.send('PONG\n')
                                incoming.close()
                            except Exception, e:
                                logging.error('Unable to reply with PONG: {0}'.format(e))
                            socketList.remove(connection)
                        else:
                            try:
                                incoming.send('FAILURE\n')
                                incoming.close()
                            except Exception, e:
                                logging.error('Unable to reply with FAILURE: {0}'.format(e))
                            socketList.remove(connection)
        logging.debug('Thread shutting down')

    def listen(self ):
        '''Iterates through self.portList and spawns a listenPort thread for each port
        '''
        for port in self.portList:
            listenThread = threading.Thread(target=self.listenPort,args=[port],name="port {0}".format(port))
            listenThread.setDaemon(True)
            listenThread.start()
            self.threads.append(listenThread)

        #while self.running:
        #    time.sleep(1)
    def connectHost(self, hostname):
        '''connects to a host and loops through and tries each port
        in self.portList in turn. Records the time it takes to connect(if successful)
        '''
        for port in self.portList:
            connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            connection.settimeout(self.timeout)
            timeDelta = time.time()
            try:
                connection.connect((hostname,port))
                failure = False
            except Exception, e:
                logging.debug('Couldn\'t connect to: {0}'.format(e))
                failure = True

            try:
                connection.send('PING\n')
                data = connection.recv(1024)
                if data == 'PONG\n':
                    #then we have a correct round trip
                    connection.close()
            except Exception, e:
                logging.debug('Unable to send PING message: {0}'.format(e))
                failure = True

            if failure:
                logging.error('failed to connect properly')
            else:
                timeDelta = time.time() - timeDelta
                #Build a string for graphite, self.graphitePrefix.hostname.port <value> <timestamp>\n
                metricString = '{0}.{1}.target.{2}.{3} {4} {5}\n'.format(self.graphitePrefix,self.hostname, hostname, port, timeDelta, int(time.time()))
                self.metrics.append(metricString)
                logging.debug('time taken for port {0}: {1}'.format(port, timeDelta))

    def connect(self):
        '''lauches a connectHost thread for all hosts in self.hostList
        '''
        while self.running:
            for host in self.hostList:
                self.connectHost(host)
                time.sleep(1)
            time.sleep(self.cycleTime)
            logging.debug(len(self.metrics))
            self.updateGraphite()


    def updateGraphite(self):
        '''Takes the array of strings that is self.metrics and pushes it to the graphite
        server specified in self.graphiteHost
        '''
        logging.debug('begin sending to graphite')
        connection = socket.socket()
        try:
            connection.connect((self.graphiteHost, self.graphitePort))
            logging.debug('connection successfull, sending graphite ')
            for metric in self.metrics:
                connection.send(metric)
            logging.debug('all metrics sent')
            self.metrics = []
            connection.close()
        except Exception, e:
            logging.error('error updating the graphite server: {0}'.format(e))



##
##If we are running directly....
##

if __name__ == '__main__':
    prober = probe()
    print prober.readConfig()
    prober.listen()
    prober.connect()


