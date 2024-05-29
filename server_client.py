import threading
import datetime
from typing import List

class Client:
    def __init__(self, socket):
        self.name = 'darius'
        self.is_connected = False
        self.socket = socket
    
    def __str__(self):
        return f"{self.name} - {self.socket.getpeername()}"

class Bid:
    def __init__(self, amount, bidder : Client):
        self.amount = amount
        self.bidder = bidder

    def __str__(self):
        return f"{self.amount}$ by {self.bidder.name}"

class Item:
    def __init__(self, name: str, min_price: int, seller : Client):
        self.name = name
        self.min_price = min_price
        self.seller = seller
        self.bids : List[Bid] = []
        self.lock = threading.Lock()
        self.is_bid_active: bool = True
        self.highest_bid: int = None
        self.expiration_time = datetime.datetime.now() + datetime.timedelta(minutes=5)

    def add_bid(self, bid: Bid):
        with self.lock:
            self.bids.append(bid)

    def get_bids(self):
        with self.lock:
            return self.bids
        
    def get_bidders(self):
        with self.lock:
            return set([bid.bidder for bid in self.bids])
        
    def __str__(self):
        if self.is_bid_active:
            return f"{self.name} - {self.min_price}$ selling by {self.seller.name} until {self.expiration_time}"
        elif len(self.bids) > 0:
            highest_bid = max(self.bids, key=lambda x: x.amount)
            return f"{self.name} - {highest_bid.amount}$ sold to {highest_bid.bidder.name}"
        else:
            return f"{self.name} - expired without any bids"