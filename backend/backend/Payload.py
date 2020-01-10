class Payload:
  counter = 0
  def __init__(self, data, clone=None):
    self.id = clone.id if clone is not None else Payload.counter
    self.data = data

    Payload.counter += 1