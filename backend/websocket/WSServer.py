"""
  WSServer - WebSocket Server library for Python

  Copyright (C) 2012 Jean Luc Biellmann (contact@alsatux.com)

  Widely inspired from:
  WebSocket client library for Python - Hiroki Ohtani(liris) - 2010

  This library is free software; you can redistribute it and/or
  modify it under the terms of the GNU Lesser General Public
  License as published by the Free Software Foundation; either
  version 2.1 of the License, or (at your option) any later version.

  This library is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
  Lesser General Public License for more details.

  You should have received a copy of the GNU Lesser General Public
  License along with this library; if not, write to the Free Software
  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import socket, threading, string, time, logging

from .WSClient import *

class WSServer(threading.Thread):
  """WebSocket Server Class
  """
  def __init__(self, host='localhost', port=9999, maxclients=20):
    super().__init__()
    self.clients = []
    self.s = ''
    self.listening = False
    self._WSHandler = None
    self.host = host
    self.port = port
    self.maxclients = maxclients

  def setWSHandler(self, handler):
    self._WSHandler = handler

  def run(self):
    """Start server
    
    Keyword Arguments:
        host {str} -- WebSocket server or ip to join. (default: {'localhost'})
        port {int} -- Port to join. (default: {9999})
        maxclients {int} -- Max clients which can connect at the same time. (default: {20})
    """
    self.s = socket.socket()
    self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.s.bind((self.host, self.port))
    self.s.listen(1)
    self.listening = True
    while self.listening:
      conn, addr = self.s.accept()
      logging.websocket('New client host/address:', addr)
      if len(self.clients) == self.maxclients:
        logging.websocket ('Too much clients - connection refused:', repr(conn))
        conn.close()
      else:
        _WSClient = WSClient(self)
        self.clients.append(_WSClient)
        logging.websocket ('Total clients:', len(self.clients))
        threading.Thread(target = _WSClient.handle, args=(conn, addr)).start()

  def send(self, bytes):
    """Send a multicast frame
    
    Arguments:
        bytes {bytes} -- Bytes to send
    """
    logging.websocket('--- SEND MULTICAST ---')
    logging.websocket(repr(bytes))
    for _WSClient in self.clients:
      _WSClient.send(bytes)
    logging.websocket('multicast send finished')

  def stop(self):
    """Stop all clients
    """
    self.listening = False
    while len(self.clients):
      self.clients.pop()._WSController.kill()
    self.s.close()
    logging.websocket('--- THAT\'S ALL FOLKS ---')

  def remove(self, _WSClient):
    if _WSClient in self.clients:
      logging.websocket('Client left:', repr(_WSClient.conn))
      self.clients.remove(_WSClient)

if __name__ == '__main__':
  server = WSServer()
  server.start(port=5001)