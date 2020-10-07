import socket

client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
client.bind(("", 2020))
while True:
    mensaje = client.recv(2020)
    print(mensaje.decode())
    #client.sendto(("respuesta").encode(),("localhost",2020))
    #print("resp enviada")