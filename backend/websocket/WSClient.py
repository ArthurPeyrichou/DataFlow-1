"""
  WSClient - WebSocket Client

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

import threading, hashlib, base64, logging
from .WSSettings import *

from .WSDecoder import *
from .WSController import *

class WSClient:
  """Socket control for a given client
  """

  # WSClient connection status
  CONNECTION_STATUS = {
    'CONNECTING': 0x0,
    'OPEN':       0x1,
    'CLOSING':    0x2,
    'CLOSED':     0x3
  }

  def __init__(self, _WSServer):
    """Constructor
    
    Arguments:
        _WSServer {WSServer} -- WebSocket Server object attached to client
    """
    self._WSServer = _WSServer
    self.conn = ''
    self.addr = ''
    self.setStatus('CLOSED')
    self._WSController = WSController(self)
    
  def setStatus(self, status=''):
    """Set current connection status
    
    Keyword Arguments:
        status {CONNECTION_STATUS} -- Status of the socket (default: {''})
    """
    if status in self.CONNECTION_STATUS:
      self.status = self.CONNECTION_STATUS[status]

  def hasStatus(self, status):
    """Test current connection status
    
    Arguments:
        status {CONNECTION_STATUS} -- Status of the socket
    """
    if status in self.CONNECTION_STATUS:
      return self.status == self.CONNECTION_STATUS[status]
    return False

  def receive(self, bufsize):
    """Real socket bytes reception
    
    Arguments:
        bufsize {int} -- Buffer size to return
    """
    bytes = self.conn.recv(bufsize) # Receive byte string
    if not bytes:
      logging.websocket('Client left', repr(self.conn))
      self._WSServer.remove(self)
      self.close()
      return b''
    return bytes

  def read(self, bufsize):
    """Try to head an amount of bytes
    
    Arguments:
        bufsize {int} -- Buffer size to fill
    """
    remaining = bufsize
    bytes = b''
    while remaining and self.hasStatus('OPEN'):
      bytes += self.receive(remaining)
      remaining = bufsize - len(bytes)
    return bytes

  def readlineheader(self):
    """Read data until line return

    Returns:
      Unicode string
    """
    line = ''
    while self.hasStatus('CONNECTING') and len(line) < 1024:
      c = self.receive(1).decode('UTF-8')
      line += c
      if c == '\n':
        break

    return line

  def handshake(self):
    """Send handshake according to RFC
    """
    headers = {}
    # Ignore first line with GET
    getRequest = self.readlineheader()
    while self.hasStatus('CONNECTING'):
      if len(headers) > 64:
        raise ValueError('Header too long.')
      line = self.readlineheader()
      if not self.hasStatus('CONNECTING'):
        raise ValueError('Client left.')
      if len(line) == 0 or len(line) == 1024:
        raise ValueError('Invalid line in header.')
      if line == '\r\n':
        break
      # Take care with strip !
      # >>> import string;string.whitespace
      # '\t\n\x0b\x0c\r'
      line = line.strip()
      # Take care with split !
      # >>> a='key1:value1:key2:value2';a.split(':',1)
      # ['key1', 'value1:key2:value2']
      kv = line.split(':', 1)
      if len(kv) == 2:
        key, value = kv
        k = key.strip().lower()
        v = value.strip()
        headers[k] = v
      else:
        raise ValueError('Invalid header key/value.')

    if not len(headers):
      raise ValueError('Reading headers failed.')
    if not 'sec-websocket-version' in headers:
      raise ValueError('Missing parameter "Sec-WebSocket-Version".')
    if not 'sec-websocket-key' in headers:
      raise ValueError('Missing parameter "Sec-WebSocket-Key".')
    if not 'host' in headers:
      raise ValueError('Missing parameter "Host".')
    if not 'origin' in headers:
      raise ValueError('Missing parameter "Origin".')

    if int(headers['sec-websocket-version']) != WSSettings.VERSION:
      raise ValueError('Wrong protocol version %s.' % WSSettings.VERSION)

    logging.websocket('--- RECEIVED HEADERS ---')
    for c in headers:
      logging.websocket (c + ':', headers[c])
    logging.websocket('------------------------')

    accept = base64.b64encode(hashlib.sha1(headers['sec-websocket-key'].encode('UTF-8') + b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest()).decode('UTF-8')

    bytes = ('HTTP/1.1 101 Switching Protocols\r\n'
         'Upgrade: websocket\r\n'
         'Connection: Upgrade\r\n'
         'Sec-WebSocket-Origin: %s\r\n'
         'Sec-WebSocket-Location: ws://%s\r\n'
         'Sec-WebSocket-Accept: %s\r\n'
         'Sec-WebSocket-Version: %s\r\n'
         '\r\n') % (headers['origin'], headers['host'], accept, headers['sec-websocket-version'])

    logging.websocket('--- HANDSHAKE ---')
    logging.websocket(bytes)
    logging.websocket('-----------------')
    self.send(bytes.encode('UTF-8'))

    return getRequest

  def handle(self, conn, addr):
    """Handle incoming datas
    
    Arguments:
        conn {socket} -- Socket of WebSocket client
        addr {address} -- Adress of WebSocket client
    """
    self.conn = conn
    self.addr = addr
    self.setStatus('CONNECTING')
    try:
      getRequest = self.handshake()
    except ValueError as error:
      self._WSServer.remove(self)
      self.close()
      raise ValueError('Client rejected: ' + str(error))
    else:
      _WSDecoder = WSDecoder()
      self.setStatus('OPEN')
      if self._WSServer._WSHandler is not None:
        self._WSServer._WSHandler.onConnect(self.conn, getRequest)
      while self.hasStatus('OPEN'):
        try:
          ctrl, data = _WSDecoder.decode(self)
        except ValueError as e:
          closing_code, message = (1000, e)
          parts = str(e).split('|')
          if len(parts) == 2:
            closing_code = int(parts[0])
            message = parts[1]
          if self.hasStatus('OPEN'):
            self._WSController.kill(closing_code, ('WSDecoder::' + str(message)).encode('UTF-8'))
          break
        else:
          logging.websocket('--- INCOMING DATAS ---')
          self._WSController.run(ctrl, data)

  def send(self, bytes):
    """Send a unicast frame
    
    Arguments:
        bytes {bytes} -- Bytes to send
    """
    if not self.hasStatus('CLOSED'):
      logging.websocket('--- SEND UNICAST ---')
      logging.websocket(repr(self.conn))
      logging.websocket(repr(bytes), '[', str(len(bytes)), ']')
      if self._WSServer._WSHandler is not None:
        self._WSServer._WSHandler.onSend(bytes)
      lock = threading.Lock()
      lock.acquire()
      self.conn.send(bytes)
      lock.release()
      logging.websocket('--- END  UNICAST ---')

  def close(self):
    """Close connection
    """
    if self._WSServer._WSHandler is not None:
      self._WSServer._WSHandler.onClose(self.conn)
    logging.websocket(repr(self.conn))
    if not self.hasStatus('CLOSED'):
      self.setStatus('CLOSED')
      self.conn.close()