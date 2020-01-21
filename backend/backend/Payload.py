import sys

class Payload:
  counter = 0
  def __init__(self, data, istID, clone=None):
    self.id = clone.id if clone is not None else Payload.counter
    self.data = data
    self.fromID = istID
    self.toID = None
    self.fromIdx = None
    self.toIdx = None

    Payload.counter += 1

  def getSize(self):
    return sys.getsizeof(self.data)
