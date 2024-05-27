import threading
import datetime

class Item:
    def __init__(self, name, price):
        self.name = name
        self.price = price
        self.bids = []
        self.lock = threading.Lock()
        self.is_bid_active = True
        self.expirationTime = datetime.datetime.now() + datetime.timedelta(minutes=5)

    def add_bid(self, bid):
        with self.lock:
            self.bids.append(bid)

    def get_bids(self):
        with self.lock:
            return self.bids
        
    def __str__(self):
        if self.is_bid_active:
            return f"{self.name} - {self.price}$ available until {self.expirationTime}"
        else:
            return f"UNAVAILABLE {self.name} - {self.price}$"

class Client:
    def __init__(self, socket):
        self.name = None
        self.is_connected = False
        self.socket = socket
    
    def __str__(self):
        return f"{self.name} - {self.socket.getpeername()}"