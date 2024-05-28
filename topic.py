import threading
from state import StateMachine
from transfer_units import Response, serialize
from server_client import Client, Item, Bid
from typing import List, Dict
import time
import scheduler
import datetime as dt

class TopicProtocol(StateMachine):
    def __init__(self, client, global_state):
        super().__init__(client, global_state)
        self.set_start('start')
        self.add_transition('start', '/connect', request_connect)
        self.add_transition('auth', '/disconnect', request_disconnect)
        self.add_transition('auth', '/list', request_get_items)
        self.add_transition('auth', '/clients', request_get_clients)
        self.add_transition('auth', '/add', request_add_item)
        self.add_transition('auth', '/bid', request_bid_item)
        self.add_transition('auth', '/info', request_item_info)


class TopicList:
  def __init__(self):
    self.clients : List[Client] = [] 
    self.items_for_sale : Dict[str, Item] = {
      'item1': Item('iphone x', 100, Client(None)),
      'item2': Item('Los Angeles Dodgers Cap semnata de Sandy Koufax', 200, Client(None)),
      'item3': Item('Lant Argint 1845', 300, Client(None)),
    }
    self.lock = threading.Lock()
    self.scheduler = scheduler.Scheduler()
    self.scheduler_thread = threading.Thread(target=self.run_jobs, daemon=True)
    self.scheduler_thread.start()
    self.scheduler.cyclic(dt.timedelta(minutes=5), self.remove_unavailable_items)

  def run_jobs(self):
    while True:
      self.scheduler.exec_jobs()
      time.sleep(1)

  def add_client(self, client: Client):
    with self.lock:
      self.clients.append(client)
  
  def remove_client(self, client: Client):
    with self.lock:
      if client in self.clients:
        self.clients.remove(client)

  def get_clients(self):
    with self.lock:
      return self.clients.copy() 

  def check_existing_name(self, name):
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
        highest_bid = max(self.items_for_sale[item.name].bids, key=lambda x: x.amount)
        print(f'Item {item.name} was sold for {highest_bid.amount}$')
        self.__notify_all_clients(f'Item {item.name} was sold for {highest_bid.amount}$ to {highest_bid.bidder.name}')
      else:
        print(f'Item {item.name} expired without any bids')
        self.__notify_all_clients(f'Item {item.name} expired without any bids')

  def remove_item(self, item: Item):
    with self.lock:
      if item.name in self.items_for_sale:
        del self.items_for_sale[item.name]
        return True
      return False

  def remove_unavailable_items(self):
    with self.lock:
      for item in self.items_for_sale.values():
        if not item.is_bid_active:
          del self.items_for_sale[item.name]

  def __check_item_availability(self, item_name):
    if item_name in self.items_for_sale and self.items_for_sale[item_name].is_bid_active:
      return self.items_for_sale[item_name]
    return None
  
  def bid_on_item(self, item_name, amount, bidder):
    with self.lock:
      item = self.__check_item_availability(item_name)
      if not item:
        return False, 'Item not available'
      if amount <= item.min_price:
        return False, 'Bid too low'
      item.add_bid(Bid(amount, bidder))
      users_to_notify = item.get_bidders()
      users_to_notify.add(item.seller)
      self.__notify_clients(users_to_notify, f'New bid on {item.name} for {amount}$ by {bidder.name}')
      return True, 'Bid placed successfully' 
    
  def get_item_info(self, item_name):
    with self.lock:
      item = self.__check_item_availability(item_name)
      if not item:
        return None
      return item
    
  def notify_all_clients(self, message):
    with self.lock:
      for c in self.clients:
        if c.is_connected:
          c.socket.sendall(serialize(Response(1, message)))
  
  def __notify_clients(self, clients, message):
    for c in clients:
      if c.is_connected:
        c.socket.sendall(serialize(Response(1, message)))

  def __notify_all_clients(self, message):
    for c in self.clients:
      if c.is_connected:
        c.socket.sendall(serialize(Response(1, message)))

  def notify_other_clients(self, client, message):
    with self.lock:
      for c in self.clients:
        if c != client and c.is_connected:
          c.socket.sendall(serialize(Response(1, message)))
  


def request_connect(request, global_state, client):
  if request.params and len(request.params) == 1:
      name = request.params[0]
      existing_name = global_state.check_existing_name(name)
      if existing_name:
        return ('start', Response(-1, 'name already exists'))
      client.name = name
      client.is_connected = True
      return ('auth', Response(0, 'You have been connected'))
  else:
      return ('start', Response(-1, 'Not enough params'))

def request_disconnect(request, global_state, client):
  client.is_connected = False
  client.name = None
  return ('start', Response(0, 'You have been disconnected'))

def request_get_items(request, global_state, client):
  items = global_state.get_items()
  if not items:
    return ('auth', Response(0, 'no items available'))
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
    try:
      amount = int(request.params[0])
    except ValueError:
      return ('auth', Response(-1, 'price must be a number'))
    item_name = request.params[1:]
    item_name = ' '.join(item_name)
    item = Item(item_name, amount, client)

    added = global_state.add_item(item)

    if not added:
      return ('auth', Response(-1, 'item already exists'))
    
    global_state.scheduler.once(item.expiration_time, global_state.mark_item_for_removal, args=(item,))
    global_state.notify_other_clients(client, f'Item {item.name} was added at price a minimum price of {item.min_price} by {client.name}')

    return ('auth', Response(0, 'item added'))
  else:
    return ('auth', Response(-1, 'not enough params'))
  
def request_bid_item(request, global_state: TopicList, client):
  if len(request.params) > 1:
    try:
      amount = int(request.params[0])
    except ValueError:
      return ('auth', Response(-1, 'amount must be a number'))
    item_name = request.params[1:]
    item_name = ' '.join(item_name)
    success, message = global_state.bid_on_item(item_name, amount, client)
    if success:
      return ('auth', Response(0, message))
    else:
      return ('auth', Response(-1, message))
  else:
    return ('auth', Response(-1, 'not enough params'))
  
def request_item_info(request, global_state: TopicList, client):
  if len(request.params) > 1:
    item_name = request.params[0:]
    item_name = ' '.join(item_name)
    item = global_state.get_item_info(item_name)

    if not item:
      return ('auth', Response(-1, 'item not available'))
    
    if item.bids:
      highest_bid = max(item.bids, key=lambda x: x.amount)
      return ('auth', Response(0, f'{item.name} - {highest_bid.amount}$ by {highest_bid.bidder.name}'))
    else:
      return ('auth', Response(0, f'{item.name} - no bids yet'))

  else:
    return ('auth', Response(-1, 'not enough params'))