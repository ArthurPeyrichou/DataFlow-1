"""
  WSEncoder - WebSocket Frame Encoder

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

import struct, array, math, random, logging
from .WSSettings import *

class WSEncoder:
  """Class to encode data frames, according to http://tools.ietf.org/html/rfc6455

  #0                   1                   2                   3
  #0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
  #+-+-+-+-+-------+-+-------------+-------------------------------+
  #|F|R|R|R| opcode|M| Payload len |    Extended payload length    |
  #|I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
  #|N|V|V|V|       |S|             |   (if payload len==126/127)   |
  #| |1|2|3|       |K|             |                               |
  #+-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
  #|     Extended payload length continued, if payload len == 127  |
  #+ - - - - - - - - - - - - - - - +-------------------------------+
  #|                               |Masking-key, if MASK set to 1  |
  #+-------------------------------+-------------------------------+
  #| Masking-key (continued)       |          Payload Data         |
  #+-------------------------------- - - - - - - - - - - - - - - - +
  #:                     Payload Data continued ...                :
  #+ - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
  #|                     Payload Data continued ...                |
  """

  def text(self, data='', fin=1, mask=1):
    """Shortcut to encode text
    
    Keyword Arguments:
        data {string} -- UTF-8 text to send. (default: {''})
        fin {bit} -- Bit which define if the frame is the last one. (default: {1})
        mask {bit} -- Bit which define is datas must be masked or not. (default: {1})
    """
    return self.encode(0x1, data, fin, mask)

  def binary(self, data=b'', fin=1, mask=1):
    """Shortcut to encode binary datas
    
    Keyword Arguments:
        data {string} -- UTF-8 text to send. (default: {''})
        fin {bit} -- Bit which define if the frame is the last one. (default: {1})
        mask {bit} -- Bit which define if datas must be masked or not. (default: {1})
    """
    return self.encode(0x2, data, fin, mask)

  def close(self, data=b'', fin=1, mask=1):
    """Shortcut to encode close frame
    
    Keyword Arguments:
        data {string} -- UTF-8 text to send. (default: {''})
        fin {bit} -- Bit which define if the frame is the last one. (default: {1})
        mask {bit} -- Bit which define id datas must be masked or not. (default: {1})
    """
    return self.encode(0x8, data, fin, mask)

  def ping(self, data=b'', fin=1, mask=1):
    """Shortcut to encode ping frame
    
    Keyword Arguments:
        data {string} -- UTF-8 text to send. (default: {''})
        fin {bit} -- Bit which define if the frame is the last one. (default: {1})
        mask {bit} -- Bit which define id datas must be masked or not. (default: {1})
    """
    return self.encode(0x9, data, fin, mask)

  def pong(self, data=b'', fin=1, mask=1):
    """Shortcut to encode pong frame
    
    Keyword Arguments:
        data {string} -- UTF-8 text to send. (default: {''})
        fin {bit} -- Bit which define if the frame is the last one. (default: {1})
        mask {bit} -- Bit which define id datas must be masked or not. (default: {1})
    """
    return self.encode(0xA, data, fin, mask)

  def encode(self, opcode=0x1, data='', fin=1, mask=1, rsv1=0, rsv2=0, rsv3=0):
    """Encoding function for all types
    
    Keyword Arguments:
        opcode {hex} -- Operation code according to RFC (default: {0x1})
        data {str} -- UTF-8 text to send (default: {''})
        fin {bit} -- Bit which define if the frame is the last one (default: {1})
        mask {bit} -- Bit which define if datas must be masked or not (default: {1})
        rsv1 {bit} -- Reserved bit for future usage. Do not use. (default: {0})
        rsv2 {bit} -- Reserved bit for future usage. Do not use. (default: {0})
        rsv3 {bit} -- Reserved bit for future usage. Do not use. (default: {0})
    """
    if not opcode in WSSettings.OPCODES:
      raise ValueError('Unknown opcode key')

    if opcode >= 0x8: # Control frames
      mask = 0x1
      fin = 0x1

    if opcode == 0x1:
      logging.websocket('Before encode:', data)
    else:
      logging.websocket('Before encode:', repr(data))

    if opcode == 0x1:
      try:
        data = data.encode('UTF-8')
      except UnicodeError:
        raise ValueError('Text datas MUST be UTF-8 encoded.')

    if mask != 0x0 and mask != 0x1:
      raise ValueError('MASK bit parameter must be 0 or 1')
    if fin != 0x0 and fin != 0x1:
      raise ValueError('FIN bit parameter must be 0 or 1')
    if rsv1 != 0x0 and rsv1 != 0x1:
      raise ValueError('RSV1 bit parameter must be 0 or 1')
    if rsv2 != 0x0 and rsv2 != 0x1:
      raise ValueError('RSV2 bit parameter must be 0 or 1')
    if rsv3 != 0x0 and rsv3 != 0x1:
      raise ValueError('RSV3 bit parameter must be 0 or 1')

    if 0x3 <= opcode <= 0x7 or 0xB <= opcode:
      raise ValueError('Reserved opcode')

    bytes = struct.pack('!B', ((fin << 7) | (rsv1 << 6) | (rsv2 << 5) | (rsv3 << 4) | opcode))

    mask_key = b''
    if mask:
      # Build a random mask key (4 bytes string)
      for i in range(4):
        mask_key += chr(int(math.floor(random.random() * 256))).encode('UTF-8')

    logging.websocket('Mask_key:', repr(mask_key))

    length = len(data)

    if length == 0:
      raise ValueError('No data given.')

    if length < 126:
      bytes += chr((mask << 7) | length).encode('UTF-8')
    elif length < (1 << 16): # 65536
      bytes += chr((mask << 7) | 0x7e).encode('UTF-8') + struct.pack('!H', length)
    elif length < (1 << 63): # 9223372036854775808
      bytes += chr((mask << 7) | 0x7f).encode('UTF-8') + struct.pack('!Q', length)
    else:
      raise ValueError('Frame too large')

    logging.websocket('Data=', data)

    ctrl = (fin, rsv1, rsv2, rsv3, opcode, mask_key, data)

    if mask:
      bytes += mask_key
      bytes += self.mask(mask_key, data)
    else:
      bytes += data

    logging.websocket('After encode:', repr(bytes))
    return bytes

  def mask(self, mask_key, bytes):
    """Mask datas
    
    Arguments:
        mask_key {4 bytes} -- Mask key
        bytes {bytes} -- Data bytes to mask
    """
    m = array.array('B', mask_key)
    j = array.array('B', bytes)
    for i in range(len(j)):
      j[i] ^= m[i % 4]
    return j.tostring()