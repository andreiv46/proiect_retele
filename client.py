import socket
import threading
import json

HOST = "localhost"
PORT = 8080

def get_status(status):
    if status == 0:
        return "Success"
    return "Error"

def listen_for_messages(sock):
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            decoded = data.decode()
            response = json.loads(decoded)
            status, message = response['status'], response['payload']
            print(f"""Message from server:
-------------------
{"Notification" if status == 1 else f"Status {get_status(status)}"}
{message}
-------------------
                  """)
            print("> ", end='', flush=True)
        except Exception as e:
            print(f"Error receiving data: {e}")
            break

def send_command(sock, command):
    try:
        sock.sendall(command.encode('utf-8'))
    except Exception as e:
        print("A aparut o eroare la trimiterea comenzi:", e)

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        print(
"""Conectat la server.
Comenzi disponibile:
    /connect <nume> - conecteaza-te la server cu numele specificat (numele trebuie sa fie unic)
    /disconnect - deconecteaza-te de la server
    /list - afiseaza toate produsele in curs de licitare
    /info <nume> - afiseaza toate licitatiile pentru un produs
    /add <pret_minim> <nume> - adauga un un produs la licitare
    /bid <pret> <nume>  - liciteaza pentru un produs           
""")
       
        listen_thread = threading.Thread(target=listen_for_messages, args=(sock,))
        listen_thread.start()

        while True:
            user_input = input("> ").strip()
            if user_input == '/exit':
                print("Trimite comanda de deconectare la server dacă este necesar.")
                break        
           
            parts = user_input.split(' ', 2)
            command = parts[0]
            params = parts[1:]

            if command in ["/connect", "/disconnect", "/list", "/clients", "/add", "/bid", "/info"]:
                send_command(sock, user_input)
            else:
                print("Unknown command.")

        listen_thread.join()

if __name__ == '__main__':
    main()