from .Component import Component
from ast import literal_eval
from threading import Timer
from pathlib import Path
from .Messages import *
import dateutil.parser
import importlib.util
import urllib.parse
import requests
import logging
import psutil
import json
import os

class Flow:
  def __init__(self, server, encoder, appPath):
    self._WSServer = server
    self.encoder = encoder
    self.appPath = os.path.join(appPath, '.flow/')

    if not os.path.exists(self.appPath):
      logging.info('Saved files folder not existing, creating...')
      os.mkdir(self.appPath)

    if not os.path.isdir(self.appPath):
      logging.error('Saved file folder is a not a folder ! Exitting')
      raise Exception('Saved folder error')

    # Variables
    self.variables = {}
    self.variablesBody = ''

    # Component library
    self.componentLibrary = {}

    # Components instances
    self.instances = {}

    # Tabs
    self.tabs = []

    # Traffic
    self.traffic = {
      'count': 0
    }

    logging.info('-- Loading designer --')
    self.load()
    logging.info('------- Loaded -------')

    # Send traffic messages
    Timer(2.0, lambda: Flow.sendTrafficMessage(self)).start()

  def sendTrafficMessage(self):
    MESSAGE_TRAFFIC['body'] = self.traffic

    MESSAGE_TRAFFIC['memory'] = str(psutil.Process(os.getpid()).memory_info()[0] / float(2 ** 20)) + 'MB'

    self.sendMessage(MESSAGE_TRAFFIC)

    # Reset inputs, outputs
    for key in self.traffic:
      if key == 'count':
        continue
      item = self.traffic[key]

      if item['ni']:
        item['input'] -= item['ni']
      if item['no']:
        item['output'] -= item['no']
      item['ni'] = 0
      item['no'] = 0
      for k in item:
        if k.startswith('no'):
          item[k] = 0

    Timer(2.0, lambda: Flow.sendTrafficMessage(self)).start()

  def load(self):
    variableFile = os.path.join(self.appPath, 'variables')
    tabsFile = os.path.join(self.appPath, 'tabs')
    componentsFile = os.path.join(self.appPath, 'instances')

    # Loading component library
    nbComponentsLoaded = 0
    componentsPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'components/')
    for file in os.listdir(componentsPath):
      if file.endswith('.py'):
        logging.info('Loading %s component' % (file,))
        # Load component
        spec = importlib.util.spec_from_file_location('components', os.path.join(componentsPath, file))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        try:
          exports = mod.EXPORTS
          if 'id' not in exports:
            logging.warn('Component %s do not possess id, dropping...' % (file,))
            continue
          if 'install' in exports:
            installFN = exports['install']
          else:
            installFN = None

          # Storing component into component library
          if exports['id'] in self.componentLibrary:
            logging.warn('Component ID already registered [%s] -> dropping' % (file,))
            continue

          # Create component obj
          obj = dict(exports)
          obj['component'] = file.split('.py')[0]
          obj['name'] = exports['title'] if 'title' in exports else file.split('.py')[0]
          obj['author'] = exports['author'] if 'author' in exports else 'No author'
          obj['color'] = exports['color'] if 'color' in exports else '#000000'
          if 'icon' in exports:
            if str(exports['icon']).startswith('fa-'):
              obj['icon'] = exports['icon'][:2]
            else:
              obj['icon'] = exports['icon']
          else:
            obj['icon'] = ''
          obj['input'] = exports['input'] if 'input' in exports and exports['input'] is not None else 0
          obj['output'] = exports['output'] if 'output' in exports and exports['output'] is not None else 0
          obj['click'] = True if 'click' in exports and exports['click'] else False
          obj['group'] = exports['group'] if 'group' in exports else 'Common'
          obj['state'] = exports['state'] if 'state' in exports else None
          obj['fn'] = installFN
          obj['readme'] = exports['readme'] if 'readme' in exports else ''
          obj['html'] = exports['html'] if 'html' in exports else ''
          obj['traffic'] = False if 'traffic' in exports and not exports['traffic'] else True
          obj['variables'] = True if 'variables' in exports and exports['variables'] else False
          obj['filename'] = file.split('.py')[0]
          self.componentLibrary[exports['id']] = obj

          data = dict(obj)
          data['fn'] = None
          data['readme'] = None
          data['html'] = None
          data['install'] = None
          data['uninstall'] = None
          if 'options' in data:
            data['options']['install'] = None
            data['options']['uninstall'] = None

          index = next(
            (i for i, item in enumerate(MESSAGE_DESIGNER['database']) if item['id'] == exports['id']),
            -1
          )

          if index == -1:
            MESSAGE_DESIGNER['database'].append(data)
          else:
            MESSAGE_DESIGNER['database'][index] = data
        except Exception as e:
          logging.warn('Exception while loading component [%s]: %s -> droppping...' % (file,e))
          continue

        nbComponentsLoaded += 1
    logging.info('%d components loaded' % (nbComponentsLoaded,))

    # Testing files
    if not os.path.exists(variableFile):
      logging.info('Variables save file not existing, creating...')
      Path(variableFile).touch()
    elif not os.path.isfile(variableFile):
      logging.error('Variables save file is not a file ! Exitting')
      raise Exception('Saved folder error')

    if not os.path.exists(componentsFile):
      logging.info('Instances save file not existing, creating...')
      Path(componentsFile).touch()
    elif not os.path.isfile(componentsFile):
      logging.error('Instances save file is not a file ! Exitting')
      raise Exception('Saved folder error')

    # Opening files
    with open(componentsFile, 'r') as file:
      data = file.read()
      file.close()
      if data is not None and data != '':
        instances = json.loads(data)
        # Recreate all components and add into MESSAGE_DESIGNER the new components
        MESSAGE_DESIGNER['components'] = []
        for ist in instances:
          newIst = self.addInstance(ist)
          if newIst is not None:
            MESSAGE_DESIGNER['components'].append(newIst.save())

    if os.path.exists(tabsFile):
      # Load existing tabs
      with open(tabsFile, 'r') as file:
        data = file.read()
        file.close()
        self.tabs = json.loads(data)
        MESSAGE_DESIGNER['tabs'] = self.tabs
    
    # Variables last because it save the designer state
    with open(variableFile, 'r') as file:
      data = file.read()
      file.close()
      self.updateVariables(data)

  def save(self):
    logging.info('---- BEGIN SAVE -----')
    with open(os.path.join(self.appPath, 'variables'), 'w') as file:
      file.write(self.variablesBody)
      file.close()

    if len(self.tabs) != 0:
      with open(os.path.join(self.appPath, 'tabs'), 'w') as file:
        file.write(json.dumps(self.tabs))
        file.close()

    with open(os.path.join(self.appPath, 'instances'), 'w') as file:
      toSave = []
      for istID in self.instances:
        toSave.append(self.instances[istID].save())
      file.write(json.dumps(toSave))
      file.close()
    logging.info('---- ENDED SAVE -----')

  def formatMessage(self, obj):
    try:
      return self.encoder.text(urllib.parse.quote(json.dumps(obj)), mask=0)
    except Exception as e:
      obj['body'] = str(obj['body'])
      return self.encoder.text(urllib.parse.quote(json.dumps(obj)), mask=0)

  def sendMessage(self, obj):
    self._WSServer.send(self.formatMessage(obj))

  def onConnect(self):
    self.sendMessage(MESSAGE_DESIGNER)

    if 'count' not in MESSAGE_ONLINE:
      MESSAGE_ONLINE['count'] = 0
    MESSAGE_ONLINE['count'] += 1
    self.sendMessage(MESSAGE_ONLINE)

  def onClose(self):
    MESSAGE_ONLINE['count'] -= 1
    self.sendMessage(MESSAGE_ONLINE)

  def onMessage(self, message, client):
    if 'type' not in message:
      if 'event' not in message:
        logging.warn('No type nor event for message, dropping...')
        return
      else:
        if message['target'] not in self.instances:
          logging.warn('Event target not known [%s] -> dropping...' % (message['target'],))
          return
        ist = self.instances[message['target']]
        ist.emit(message['event'])
        return

    if message['type'] == 'variables':
      self.updateVariables(message['body'])
    elif message['type'] == 'getvariables':
      MESSAGE_VARIABLES['body'] = self.variablesBody
      self.sendMessage(MESSAGE_VARIABLES)
    elif message['type'] == 'apply':
      self.applyChanges(message['body'])
    elif message['type'] == 'readme':
      comName = message['target']
      if comName not in self.componentLibrary:
        logging.warn('Component name not found in library [%s] -> dropping...' % (comName,))
        return
      MESSAGE_STATIC['id'] = message['id']
      MESSAGE_STATIC['body'] = self.componentLibrary[comName]['readme']
      client.send(self.formatMessage(MESSAGE_STATIC))
    elif message['type'] == 'html':
      if message['target'] not in self.componentLibrary:
        logging.warn('Component not found in library [%s] -> dropping...' % (message['target'],))
        return
      com = self.componentLibrary[message['target']]
      MESSAGE_STATIC['id'] = message['id']
      MESSAGE_STATIC['body'] = com['html']
      client.send(self.formatMessage(MESSAGE_STATIC))
    elif message['type'] == 'options':
      if message['target'] not in self.instances:
        logging.warn('Options target not existing [%s] -> dropping...' % (message['target'],))
        return

      com = self.instances[message['target']]

      old_options = com.options
      new_options = message['body']
      com.options = new_options

      if 'comname' in new_options:
        com.name = new_options['comname']
        del com.options['comname']
      else:
        com.name = ''
      if 'comreference' in new_options:
        com.reference = new_options['comreference']
        del com.options['comreference']
      else:
        com.reference = None

      if 'comcolor' in new_options:
        com.color = new_options['comcolor']
        del com.options['comcolor']
      if 'comnotes' in new_options:
        com.notes = new_options['comnotes']
        del com.options['comnotes']

      # TODO: inputs, outputs

      'options' in com.events and com.emit('options', com.options, old_options)

      # TODO: Refresh connections
      self.save()
    elif message['type'] == 'clearerrors':
      for ist in self.instances:
        self.instances[ist].errors = {}

      self.save()
      self.sendMessage(MESSAGE_CLEARERRORS)
    elif message['type'] == 'install':
      # New component
      if 'body' not in message:
        message['body'] = None
      self.install(message['filename'], message['body'])
    else:
      logging.warn('Message type unknown [%s] -> dropping...' % (message['type'],))

  def install(self, filename, body):
    componentsPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'components/')

    # Check if the filename is an URL
    if filename[:6] == 'http:/' or filename == 'https:':
      # Fill body variable
      r = requests.get(filename)
      body = r.content

      filename = os.path.basename(urllib.parse(filename))

    if filename[-3:] != '.py':
      logging.warn('File not ending with .py [%s] dropping...' % (filename,))
      return

    saved = False
    filepath = os.path.join(componentsPath, filename)
    if os.path.exists(filepath):
      os.rename(filepath, filepath + '-save')
      saved = True
    
    with open(filepath, 'w') as file:
      file.write(body)
      file.close()

    # Check if exports of the file contains install func
    try:
      spec = importlib.util.spec_from_file_location('components', filepath)
      mod = importlib.util.module_from_spec(spec)
      spec.loader.exec_module(mod)

      if not hasattr(mod, 'EXPORTS') or 'install' not in mod.EXPORTS:
        logging.warn('Imported module not in the right format. No install function...')
        MESSAGE_ERROR['body'] = 'Incorrect module, no install functions in EXPORTS variable !'
        self.sendMessage(MESSAGE_ERROR)
        os.remove(filepath)
        if saved:
          os.rename(filepath + '-save', filepath)
    except Exception as e:
      logging.error('Error while importing file [%s]: %s' % (filename, e))
      MESSAGE_ERROR['body'] = str(e)
      self.sendMessage(MESSAGE_ERROR)

  def updateVariables(self, body):
    # Parse variables and update them
    newVariables = {}
    try:
      logging.info('-- Refreshing variables --')
      parts = body.split('\n')
      for p in parts:
        if len(p) == 0 or p[0] == '#' or p[:2] == '//':
          continue

        idx = p.find(':')
        if idx == -1:
          continue

        name = p[:idx].strip()
        value = p[idx+1:].strip()

        idx = name.find('(')
        if idx != -1:
          subtype = name[idx+1:name.find(')')].strip().lower()
          name = name[:idx].strip()
        else:
          subtype = ''

        logging.info('%s [%s] = %s' % (name, (subtype if subtype != '' else 'no type specified'), value))

        if subtype == '':
          newVariables[name] = value
        elif subtype == 'string':
          newVariables[name] = value
        elif subtype == 'number' or subtype == 'float' or subtype == 'double' or subtype == 'currency':
          newVariables[name] = float(value)
        elif subtype == 'boolean' or subtype == 'bool':
          newVariables[name] = bool(value)
        elif subtype == 'json':
          newVariables[name] = json.loads(value)
        elif subtype == 'date' or subtype == 'datetime' or subtype == 'time':
          newVariables[name] = dateutil.parser.parse(value)
        elif subtype == 'array':
          newVariables[name] = literal_eval(value)
        else:
          raise ValueError('Type of variable not handled [%s]' % (subtype,))
      self.variables = newVariables
      self.variablesBody = body
      logging.info('----- End refreshing -----')

      # Save designer
      self.save()
      self.sendMessage({
        'type': 'variables-saved'
      })
    except Exception as e:
      self.sendMessage({
        'type': 'variables-error',
        'body': str(e)
      })

  def applyChanges(self, body):
    componentsToAdd = []
    componentsToRemove = []
    for change in body:
      if 'type' not in change:
        logging.warn('No type for change, dropping...')
        continue

      type = change['type']
      if type == 'add':
        # Add component to list
        componentsToAdd.append(change['com'])
      elif type == 'rem':
        componentsToRemove.append(change['id'])
      elif type == 'tabs':
        self.tabs = change['tabs']
        MESSAGE_DESIGNER['tabs'] = change['tabs']
      elif type == 'mov':
        target = change['com']['id']
        if target not in self.instances:
          logging.warn('Component to move not in instances [%s] -> dropping...' % (target,))
          continue
        self.instances[target].setPos(change['com']['x'], change['com']['y'])
      elif type == 'conn':
        if change['id'] not in self.instances:
          logging.warn('New connection target not in instances [%s] -> dropping...' % (change['id'],))
          continue

        self.instances[change['id']].updateConnections(change['conn'])
      else:
        logging.warn('Type not handled for change [%s] -> dropping...' % (type,))

    # Apply changes
    for id in componentsToRemove:
      if id not in self.instances:
        logging.warn('ID to remove not in instances [%s] -> dropping...' % (id,))
        continue
      del self.instances[id]

    for com in componentsToAdd:
      self.addInstance(com)

    # Save after changes
    self.save()

    # Redo MESSAGE_DESIGNER['components']
    MESSAGE_DESIGNER['components'] = []
    for instID in self.instances:
      MESSAGE_DESIGNER['components'].append(self.instances[instID].save())
    # Send to all other users
    self.sendMessage(MESSAGE_DESIGNER)

  def addInstance(self, com):
    comID = com['id']
    if comID not in self.instances:
      # New instance
      component = com['component']
      if component not in self.componentLibrary:
        logging.warn('Component not in library [%s] -> dropping...' % (component,))
        return None
      libraryOpts = self.componentLibrary[component]
      newInst = Component(com, libraryOpts, self)
      if 'fn' in libraryOpts or 'install' in libraryOpts:
        libraryOpts['fn'](newInst)
      self.instances[comID] = newInst

      return newInst
    else:
        logging.warn('Component already existing [%s] -> dropping...' % (comID,))
        return None

  def updateTraffic(self, id, type, count, index=None):
    if not id in self.traffic:
      self.traffic[id] = {
        'input': 0,
        'output': 0,
        'pending': 0,
        'duration': 0,
        'ci': 0,
        'co': 0,
        'ni': 0,
        'no': 0
      }

    if type == 'pending' or type == 'duration' or type == 'ci' or type == 'co':
      self.traffic[id][type] = count
    elif type == 'output':
      self.traffic[id][type] += 1
      self.traffic[id]['no'] += 1

      if index is not None:
        k = 'no' + str(index)
        if k not in self.traffic[id]:
          self.traffic[id][k] = 0
        self.traffic[id][k] += 1

      self.traffic['count'] += 1
    elif type == 'input':
      if count is not True:
        self.traffic[id][type] += 1
      self.traffic[id]['ni'] += 1
    else:
      self.traffic[id][type] += 1
