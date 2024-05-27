import socket
import threading

HOST = "localhost"
PORT = 8080

def listen_for_messages(sock):
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            print(f"""Message from server:
-------------------
{data.decode()}
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
        print("A apărut o eroare la trimiterea comenzi:", e)

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        print("Conectat la server. Introduceți comenzi. Scrie 'exit' pentru a ieși.")
       
        listen_thread = threading.Thread(target=listen_for_messages, args=(sock,))
        listen_thread.start()

        while True:
            user_input = input("> ").strip()
            if user_input == 'exit':
                print("Trimite comanda de deconectare la server dacă este necesar.")
                break        
           
            parts = user_input.split(' ', 2)
            command = parts[0]
            params = parts[1:]

            if command in ["connect", "list", "clients", "add"]:
                send_command(sock, user_input)
            else:
                print("Unknown command.")

        listen_thread.join()

if __name__ == '__main__':
    main()