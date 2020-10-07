import socket
import time

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
# Set a timeout so the socket does not block
# indefinitely when trying to receive data.
# server.settimeout(0.2)
server.bind(("", 2021))
if True:
    server.sendto("prengunta".encode(), ("<broadcast>", 2020))
    print("preg enviada")
    respuesta = server.recv(1024) #buffer
    print (respuesta.decode())