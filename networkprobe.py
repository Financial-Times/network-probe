#!/usr/bin/env python

import yaml
import time
import socket
import select
import logging
import threading
logging.basicConfig(level=logging.DEBUG)
class probe(object):
    '''This class consists of two parts: a listening part that holds
    open a number of sockets, and a connector that connects to those sockets

    The idea is to measure connectivity between two or more networks.
    '''

    def __init__(self, configFile = 'config.yml'):
        '''ENGAGE
        '''
        self.configFile     = configFile
        self.portList       = []
        self.hostList       = []
        self.running        = True
        self.threads        = []

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
                self.portList = config['portlist']
                self.hostList = config['hosts']
            except Exception, e:
                logging.error("Error in config file: {0}\n\tThis is possibly a typo".format(e))

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
    def listen(self):
        '''Iterates through self.portList and spawns a listenPort thread for each port
        '''
        for port in self.portList:
            listenThread = threading.Thread(target=self.listenPort,args=[port],name="port{0}".format(port))
            listenThread.setDaemon(True)
            listenThread.start()
            self.threads.append(listenThread)

        while self.running:
            time.sleep(1)

