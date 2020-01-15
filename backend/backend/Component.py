from .Payload import Payload
from .Messages import *
import logging

class Component:
  def __init__(self, attrs, libraryOpts, flowInstance):
    self.id = attrs['id']
    self.x = attrs['x']
    self.y = attrs['y']
    self.state = attrs['state']
    self.tab = attrs['tab']
    self.component = attrs['component']
    self.disabledio = attrs['disabledio']
    self.connections = attrs['connections']
    self.custom = {}

    # Apply component library attrs
    self.name = attrs['name'] if 'name' in attrs else libraryOpts['name']
    self.color = attrs['color'] if 'color' in attrs else libraryOpts['color']
    if 'icon' in libraryOpts:
      if str(libraryOpts['icon']).startswith('fa-'):
        self.icon = libraryOpts['icon'][:2]
      else:
        self.icon = libraryOpts['icon']
    else:
      self.icon = ''
    self.notes = attrs['notes'] if 'notes' in attrs else ''
    self.options = attrs['options'] if 'options' in attrs else (libraryOpts['options'] if 'options' in libraryOpts else {})

    # Save link to flow instance
    self.flow = flowInstance

    # Component events
    self.events = {}

    # Connections
    self.connections = attrs['connections'] if 'connections' in attrs else {}

    # Traffic
    self.countInputs = 0
    self.countOutputs = 0
    self.outputComponentAlreadyListed = {}

    # Errors
    self.errors = {}

  def setPos(self, x, y):
    self.x = x
    self.y = y

  def status(self, text='', color='gray'):
    # Check if the status changes
    if text == self.state['text'] and color == self.state['color']:
      return self
    
    # Apply change and notify
    self.state['text'] = text
    self.state['color'] = color

    MESSAGE_STATUS['target'] = self.id
    MESSAGE_STATUS['body'] = self.state

    self.flow.sendMessage(MESSAGE_STATUS)

  def on(self, eventName, func):
    if eventName in self.events:
      logging.warn('Event already registered on component [%s, %s] -> replacing...' % (self.id, eventName))

    self.events[eventName] = func

  def emit(self, eventName, *args):
    if eventName not in self.events:
      logging.warn('Event not registered for this component [%s, %s] -> dropping...' % (self.id, eventName))
      return

    self.events[eventName](self, args)

  def debug(self, data, style=None, group=None, id=None):
    MESSAGE_DEBUG['group'] = group

    if isinstance(data, Exception):
      MESSAGE_DEBUG['body'] = {
        'error' : data.message,
        'stack': ''
      }
    else:
      MESSAGE_DEBUG['body'] = data

    MESSAGE_DEBUG['identificator'] = id
    MESSAGE_DEBUG['time'] = None
    MESSAGE_DEBUG['style'] = style if style is not None else 'info'
    MESSAGE_DEBUG['id'] = self.id
    self.flow.sendMessage(MESSAGE_DEBUG)

  def updateConnections(self, conn):
    self.connections = conn if conn is not None else {}

  def send(self, data, index=None):
    if not isinstance(data, Payload):
      data = Payload(data)

    if index is not None:
      index = str(index)

    # Reset list
    self.outputComponentAlreadyListed = {}

    if index is None:
      # Send through all outputs
      # {'0': [{'index': '0', 'id': '1578503223401'}]}
      for conn in self.connections:
        if conn != '99': # Ignore bug output
          self.flow.updateTraffic(self.id, 'output', None, conn, size=data.getSize())
          self.sendToIndex(data, conn)
    else:
      self.flow.updateTraffic(self.id, 'output', None, index, size=data.getSize())
      if index not in self.connections:
        logging.warn('No output connection with this index [%s] -> dropping...' % (index,))
        return

      self.sendToIndex(data, index)

    # self.flow.sendTrafficMessage()

  def error(self, error, parent=None):
    key = None

    if isinstance(parent, Component):
      key = parent.id
    elif parent is not None:
      key = parent
    else:
      key = 'error'

    if key not in self.errors:
      self.errors[key] = { 'count': 0 }
    self.errors[key]['error'] = error
    self.errors[key]['count'] += 1

    MESSAGE_ERRORS['id'] = self.id
    MESSAGE_ERRORS['body'] = self.errors

    self.flow.sendMessage(MESSAGE_ERRORS)
    self.throw(error)

    if 'error' in self.events:
      self.emit('error', error, parent)

  def throw(self, data):
    self.send(data, 99)

  def sendToIndex(self, data, index):
    targets = self.connections[str(index)]
    # targets -> [{'index': '0', 'id': '1578503223401'}]
    for t in targets:
      if t['id'] not in self.flow.instances:
        logging.warn('Sending to unknown component [%s] -> dropping...' % (t['id'],))
        continue
      
      ist = self.flow.instances[t['id']]

      # Disable inputs
      if t['index'] in ist.disabledio['input']:
        continue

      # Update traffic
      ist.countInputs += 1

      if ist.id not in self.outputComponentAlreadyListed:
        self.outputComponentAlreadyListed[ist.id] = True
        self.flow.updateTraffic(ist.id, 'input', False, size=data.getSize())

      if ist.id in self.flow.traffic:
        self.flow.traffic[ist.id]['ci'] = ist.countInputs

      self.flow.sendTrafficMessage()

      # Keep trace of data send
      self.flow.onGoing += 1
      ist.emit('data', data)
      self.flow.onGoing -= 1
      if self.flow.onGoing == 0:
        self.flow.resetTraffic()

  def save(self):
    objToSave = {
      'id': self.id,
      'component': self.component,
      'x': self.x,
      'y': self.y,
      'state': self.state,
      'tab': self.tab,
      'disabledio': self.disabledio,
      'connections': self.connections,
      'state': self.state,
      'name': self.name,
      'color': self.color,
      'icon': self.icon,
      'notes': self.notes,
      'options': self.options
    }

    return objToSave
