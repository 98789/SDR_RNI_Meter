#!/usr/bin/env python

from socket import socket
from socket import AF_INET
from socket import SOCK_STREAM
from json import dumps
from json import loads

class remote_configurator():
    """Set TCP connection to send/receive configurations"""

    def __init__(self, host, port, buffer_size=1024):
        self.host = host
        self.port = port
        self.buffer_size = buffer_size

    def set_socket(self):
        """Set TCP socket"""
        self.s = socket(AF_INET, SOCK_STREAM)

    def bind(self):
        """bind TCP connection"""

        self.set_socket()
        self.s.bind((self.host, self.port))
        self.s.listen(1)

    def listen(self, timeout=0):
        """Listen to incoming configurations"""

        if timeout:
            self.s.settimeout(timeout)
        try:
            conn, addr = self.s.accept()
        except:
            return {}
        data = loads(conn.recv(self.buffer_size))
        conn.close()

        return data


    def send(self, conf):
        """Send device configurations remotely"""

        self.set_socket()
        if not isinstance(conf, dict):
            raise TypeError('conf must be a dict')
        conf = dumps(conf)
        self.s.connect((self.host, self.port))
        self.s.send(conf)
        self.s.close()
