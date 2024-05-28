import json

class Request:
  def __init__(self, command, params):
    self.type = command
    self.params = params

class Response:
  def __init__(self, status, payload):
    self.status = status
    self.payload = payload

def serialize(response):
  return bytes(json.dumps({'status': response.status, 'payload': response.payload}), encoding='utf-8')

def deserialize(request):
  items = request.decode('utf-8').strip().split(' ')
  if (len(items) > 1):
    return Request(items[0], items[1:])
  return Request(items[0], None)