"""
  WSMain - WebSocket Main

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

"""
SCHEME:

  WSMain (Startup)   incoming datas
    |                       |
    v                       v
WSServer (listen) => WSClient (thread) -> WSDecoder (one per WSClient)
    ^                       ^                  |
    |                       |                  |
    |                       |                  |
    |                       |                  v
    |                       |           WSController (one per WSClient)
    |                    unicast               |
    |                       |                  |
    |                       |                  |
    |                       |                  v
    |-------multicast-------|------------- WSEncoder
"""

from backend.LoggerFormater import (LoggerFormatter, loggingWebsocket)
from websocket.WSEncoder import WSEncoder
from backend.WSHandler import WSHandler
from websocket.WSServer import WSServer
from backend.Flow import Flow
import threading
import argparse
import logging
import sys
import os

if __name__ == "__main__":
  # Configuring arguments
  parser = argparse.ArgumentParser()
  parser.add_argument('-v', '--verbose', help='Show all logs', action='store_true')
  parser.add_argument('-l', '--location', help='Location of saved files, default is where you launch the command')
  args = parser.parse_args()

  # Configuring logging
  fmt = LoggerFormatter()
  hdlr = logging.StreamHandler(sys.stdout)
  hdlr.setFormatter(fmt)
  logging.root.addHandler(hdlr)
  logging.root.setLevel(logging.DEBUG)
  
  if args.verbose:
    logging.websocket = loggingWebsocket
  else:
    logging.websocket = (lambda *argv: None)

  if args.location:
    location = args.location
  else:
    location = './'

  try:
    pid = os.getpid()
    _WSServer = WSServer(host='', port=5001, maxclients=20)
    flow = Flow(_WSServer, WSEncoder(), location)
    _WSHandler = WSHandler(_WSServer, flow)
    _WSServer.start()
    input('Server listening, press any key to abort...\n')
    logging.info('--- KEYBOARD INTERRUPT ---')
    _WSServer.stop()
    os.kill(pid, 9)
  except KeyboardInterrupt as e:
    logging.info('--- KEYBOARD INTERRUPT ---')
    _WSServer.stop()
    os.kill(pid, 9)
