import urllib.parse
import logging
import json
import re

class WSHandler:
  def __init__(self, server, flowInstance):
    self._WSServer = server
    self._WSServer.setWSHandler(self)
    self.flow = flowInstance

  def onConnect(self, conn, request):
    logging.info('--- NEW CLIENT CONNECTED ---')
    logging.info('- REQUEST: %s' % (request.rstrip(),))
    # Compute parameters
    url = request.split('GET ')[1].split(' HTTP')[0]
    params = re.findall(r'([^?=&]+=[^&]*)', url)
    if len(params) > 0:
      logging.info('- PARAMS:')
      for p in params:
        logging.info('\t* ' + p[:p.index('=')] + (' = ' + p[p.index('=')+1:] if p.index('=') != len(p)-1 else ''))
    logging.info('----------------------------')
    self.flow.onConnect()

  def onMessage(self, message, client):
    logging.info('----- INCOMING MESSAGE -----')
    logging.info(message)
    logging.info('- DECODING...')
    message = json.loads(urllib.parse.unquote(message))
    logging.info('- MESSAGE: %s' % (message,))
    logging.info('----------------------------')
    self.flow.onMessage(message, client)

  def onSend(self, message):
    logging.info('----- SENDING  MESSAGE -----')
    logging.info(message)
    logging.info('----------------------------')

  def onClose(self, conn):
    logging.info('----- CLOSE (WSCLIENT) -----')
    self.flow.onClose()
