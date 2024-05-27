import threading
from state import StateMachine
from transfer_units import Response, serialize
from server_client import Client, Item
from typing import List, Dict
import schedule
import time

class TopicProtocol(StateMachine):
    def __init__(self, client, global_state):
        super().__init__(client, global_state)
        self.set_start('start')
        self.add_transition('start', 'connect', request_connect)
        self.add_transition('auth', 'disconnect', request_disconnect)
        self.add_transition('auth', 'list', request_get_items)
        self.add_transition('auth', 'clients', request_get_clients)
        self.add_transition('auth', 'add', request_add_item)


class TopicList:
  def __init__(self):
    self.clients : List[Client] = [] 
    self.items_for_sale : Dict[str, Item] = {
      'item1': Item('item1', 100),
      'item2': Item('item2', 200),
      'item3': Item('item3', 300),
    }
    self.lock = threading.Lock()
    self.scheduler = schedule.Scheduler()
    self.scheduler_thread = threading.Thread(target=self.run_jobs, daemon=True)
    self.scheduler_thread.start()
  
  def one_job(self, callback, *args):
    callback(*args)
    return schedule.CancelJob
  
  def run_jobs(self):
    while True:
      self.scheduler.run_pending()
      time.sleep(1)

  def add_client(self, client: Client):
    with self.lock:
      self.clients.append(client)
  
  def remove_client(self, client: Client):
    with self.lock:
      self.clients.remove(client)

  def get_clients(self):
    with self.lock:
      return self.clients 

  def checkExistingName(self, name):
    with self.lock:
      if self.clients == []:
        return False
      for client in self.clients:
        if client.name == name:
          return True
      return False
  
  def get_items(self):
    with self.lock:
      return list(self.items_for_sale.values())  

  def add_item(self, item: Item):
    with self.lock:
      if item.name in self.items_for_sale:
        return False
      self.items_for_sale[item.name] = item
      return True
    
  def mark_item_for_removal(self, item: Item):
    with self.lock:
      print(f'Item {item.name} expired. Removing it from sale.')
      self.items_for_sale[item.name].is_bid_active = False
      if self.items_for_sale[item.name].bids:
        print(f'Item {item.name} was sold for {max(self.items_for_sale[item.name].bids).amount}$')
        highest_bid = max(self.items_for_sale[item.name].bids)
        self._notify_all_clients(f'Item {item.name} was sold for {highest_bid.amount}$')
      else:
        print(f'Item {item.name} expired without any bids')
        self._notify_all_clients(f'Item {item.name} expired without any bids')

  def remove_item(self, item: Item):
    with self.lock:
      if item.name in self.items_for_sale:
        del self.items_for_sale[item.name]
        return True
      return False
    
  def notify_all_clients(self, message):
    with self.lock:
      for c in self.clients:
        if c.is_connected:
          c.socket.sendall(serialize(Response(0, message)))

  def _notify_all_clients(self, message):
    for c in self.clients:
      if c.is_connected:
        c.socket.sendall(serialize(Response(0, message)))

  def notify_other_clients(self, client, message):
    with self.lock:
      for c in self.clients:
        if c != client and c.is_connected:
          c.socket.sendall(serialize(Response(0, message)))
  


def request_connect(request, global_state, client):
  if request.params and len(request.params) == 1:
      name = request.params[0]
      existingName = global_state.checkExistingName(name)
      if existingName:
        return ('start', Response(-1, 'name already exists'))
      client.name = name
      client.is_connected = True
      return ('auth', Response(0, 'you are in'))
  else:
      return ('start', Response(-1, 'not enough params'))

def request_disconnect(request, global_state, client):
  client.is_connected = False
  client.name = None
  return ('start', Response(0, 'you are now out'))

def request_get_items(request, global_state, client):
  items = global_state.get_items()
  items = [str(item) for item in items]
  items = '\n'.join(items)
  return ('auth', Response(0, items))

def request_get_clients(request, global_state, client):
  clients = global_state.get_clients()
  clients = [str(client) for client in clients]
  clients = '\n'.join(clients)
  return ('auth', Response(0, clients))

def request_add_item(request, global_state: TopicList, client):
  if len(request.params) > 1:
    item = Item(request.params[0], request.params[1])

    added = global_state.add_item(item)

    if not added:
      return ('auth', Response(-1, 'item already exists'))
    
    expirationTime = item.expirationTime.strftime("%H:%M:%S")
    global_state.scheduler.every().day.at(expirationTime).do(global_state.one_job, global_state.mark_item_for_removal, item)
    
    global_state.notify_other_clients(client, f'Item {item.name} added at price {item.price}')

    return ('auth', Response(0, 'item added'))
  else:
    return ('auth', Response(-1, 'not enough params'))