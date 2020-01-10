"""
  WSController - WebSocket Controller

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
import logging
from .WSSettings import *
from .WSEncoder import *

class WSController:
  """WebSocket Controller Class

  OPCODE USED:
  1000: NORMAL_CLOSURE
  1011: UNEXPECTED_CONDITION_ENCOUNTERED_ON_SERVER
  """
  def __init__(self, _WSClient):
    """Constructor
    
    Arguments:
        _WSClient {WSClient} -- Client
    """
    self._WSClient = _WSClient

  def array_shift(self, bytes, n):
    """Pop n bytes
    
    Arguments:
        bytes {bytes} -- Bytes to shift
        n {int} -- Number if bytes to shift
    """
    out = b''
    for num in range(0, n):
      out += chr(bytes[num]).encode('UTF-8')
    return out, bytes[n:]

  def run(self, ctrl, data):
    """Handle incoming datas
    
    Arguments:
        ctrl {ctrl} -- Control dictionnary for data
        data {string} -- Decoded data, text or binary
    """
    logging.websocket('--- CONTROLLER ---')
    logging.websocket(repr(self._WSClient.conn))
    _WSEncoder = WSEncoder()

    # CONTROLS
    if ctrl['opcode'] == 0x9: # PING
      logging.websocket('--- PING FRAME --- ')
      logging.websocket(repr(self._WSClient.conn))
      try:
        bytes = _WSEncoder.pong('Application data')
      except ValueError as error:
        self._WSClient._WSServer.remove(self._WSClient)
        self.kill(1011, 'WSEncoder error: ' + str(error))
      else:
        self._WSClient.send(bytes)

    if ctrl['opcode'] == 0xA: # PONG
      logging.websocket('--- PONG FRAME ---')
      logging.websocket(repr(self._WSClient.conn))
      if len(data):
        logging.websocket('Pong frame datas:', str(data))

    if ctrl['opcode'] == 0x8: # CLOSE
      logging.websocket('--- CLOSE FRAME ---')
      logging.websocket(repr(self._WSClient.conn))
      self._WSClient._WSServer.remove(self._WSClient)
      # closing was initiated by server
      if self._WSClient.hasStatus('CLOSING'):
        self._WSClient.close()
      # closing was initiated by client
      if self._WSClient.hasStatus('OPEN'):
        self._WSClient.setStatus('CLOSING')
        self.kill(1000, b'Goodbye !')
      # the two first bytes MUST contains the exit code, follow optionnaly with text data not shown to clients
      if len(data) >= 2:
        code, data = self.array_shift(data,2)
        status = ''
        if code in WSSettings.CLOSING_CODES:
          logging.websocket('Closing frame code:', code)
        if len(data):
          logging.websocket('Closing frame data:', data)

    # DATAS
    if ctrl['opcode'] == 0x1: # TEXT
      logging.websocket('--- TEXT FRAME ---')
      logging.websocket(repr(self._WSClient.conn))
      if len(data):
        try:
          # Handle message if possible
          if self._WSClient._WSServer._WSHandler is not None:
            self._WSClient._WSServer._WSHandler.onMessage(data, self._WSClient)
        except ValueError as error:
          self._WSClient._WSServer.remove(self._WSClient)
          self.kill(1011, ('WSEncoder error: ' + str(error)).encode('UTF-8'))

    if ctrl['opcode'] == 0x0: # CONTINUATION
      logging.websocket('--- CONTINUATION FRAME ---', repr(self._WSClient.conn))
      pass

    if ctrl['opcode'] == 0x2: # BINARY
      logging.websocket('--- BINARY FRAME ---', repr(self._WSClient.conn))
      pass

  def ping(self):
    """Send a ping
    """
    logging.websocket('--- PING (CONTROLLER) ---')
    if self._WSClient.hasStatus('OPEN'):
      _WSEncoder = WSEncoder()
      try:
        bytes = _WSEncoder.ping(b'Application data')
      except ValueError as error:
        self._WSClient._WSServer.remove(self._WSClient)
        self.kill(1011, 'WSEncoder error: ' + str(error))
      else:
        self._WSClient.send(bytes)

  ## Force to close the connection
  #  @param code Closing code according to RFC. Default is 1000 (NORMAL_CLOSURE).
  #  @param error Error message to append on closing frame. Default is empty.

  def kill(self, code=1000, error=b''):
    """Force to close the connection
    
    Keyword Arguments:
        code {int} -- Closing code according to RFC. (default: {1000})
        error {bytes} -- Error message to append on closing frame. (default: {''})
    """
    logging.websocket('--- KILL (CONTROLLER)  ---', repr(self._WSClient.conn))
    if not self._WSClient.hasStatus('CLOSED'):
      _WSEncoder = WSEncoder()
      data = struct.pack('!H', code)
      if len(error):
        data += error
      logging.websocket('--- KILL FRAME ---')
      logging.websocket('Code:', code)
      logging.websocket('Error:', error)
      logging.websocket(repr(self._WSClient.conn))
      try:
        bytes = _WSEncoder.close(data)
      except ValueError as error:
        self._WSClient.close()
      else:
        self._WSClient.send(bytes)
        self._WSClient.close()