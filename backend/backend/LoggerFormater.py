import logging

WEBSOCKET_LOG_LEVEL = 25

def loggingWebsocket(*argv):
  string = ''
  for arg in argv:
    string += str(arg) + ' '
  logging.log(WEBSOCKET_LOG_LEVEL, string)

class bcolors:
  BLACK = '\033[30m'
  RED = '\033[31m'
  GREEN = '\033[32m'
  YELLOW = '\033[33m'
  BLUE = '\033[34m'
  MAGENTA = '\033[35m'
  CYAN = '\033[36m'
  WHITE = '\033[37m'
  ENDC = '\033[0m'
  BOLD = '\033[1m'
  UNDERLINE = '\033[4m'

class LoggerFormatter(logging.Formatter):
  levelsColors = {
    logging.ERROR: bcolors.RED,
    logging.WARN: bcolors.YELLOW,
    WEBSOCKET_LOG_LEVEL: bcolors.CYAN,
    logging.INFO: bcolors.BLUE,
    logging.DEBUG: bcolors.MAGENTA
  }

  def __init__(self, fmt="%(levelno)s: %(msg)s"):
    super().__init__(fmt=fmt, datefmt=None, style='%')

  def format(self, record):
    format_orig = self._style._fmt

    if record.levelno in LoggerFormatter.levelsColors:
      self._style._fmt = LoggerFormatter.levelsColors[record.levelno] + "%(msg)s" + bcolors.ENDC

    result = logging.Formatter.format(self, record)

    self._style._fmt = format_orig

    return result