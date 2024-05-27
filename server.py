import socket 
import threading
from topic import TopicList, TopicProtocol
from transfer_units import Request, Response, serialize, deserialize
from server_client import Client


class Server:
    def __init__(self, host='localhost', port=8080):
        self.host = host
        self.port = port
        self.global_state = TopicList()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))

    def handle_client_write(self, client_socket, response):
        client_socket.sendall(serialize(response))

    def handle_client_read(self, client : Client):
        try:
            protocol = TopicProtocol(client, self.global_state)
            while True:
                if client.socket == None:
                    break
                data = client.socket.recv(1024)
                if not data:
                    break
                unpacked_request = deserialize(data)
                response = protocol.process_command(unpacked_request)
                self.handle_client_write(client.socket, response)

        except Exception as e:
            print(e)
            print(f"Client {client.socket} has disconnected")
            self.global_state.remove_client(client)          

    def accept(self):
        while True:
            client_socket, addr = self.server.accept()
            client = Client(client_socket)
            self.global_state.add_client(client)
            print(f"{addr} has connected")
            items = self.global_state.get_items()
            for item in items:
                print(item)
            client_read_thread = threading.Thread(target=self.handle_client_read, args=(client,))
            client_read_thread.start()

    def start(self):
        self.server.listen()
        print(f"[*] Listening on {self.host}:{self.port}")
        accept_thread = threading.Thread(target=self.accept)
        accept_thread.start()
        accept_thread.join()

    def stop(self):
        print("Stopping server...")
        self.server.close()

if __name__ == "__main__":
    server = Server()
    try:
        server.start()
    except BaseException as err:
        print(err)
    finally:
        server.stop()

