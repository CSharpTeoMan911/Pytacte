import socket

HOST = "127.0.0.1"
PORT=80

server = socket.socket(family=socket.AddressFamily.AF_INET, type=socket.SocketKind.SOCK_STREAM)

def main():
    server.bind((HOST, PORT))
    server.listen()

if __name__ == "__main__":
    main()