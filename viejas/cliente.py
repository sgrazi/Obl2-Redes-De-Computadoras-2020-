import socket

mi_socket = socket.socket()
mi_socket.connect( ('25.92.62.202',2020) )
mi_socket.sendto(("Hola desde el cliente").encode(),('localhost',2020))
respuesta = mi_socket.recv(1024) #buffer
print (respuesta.decode())
mi_socket.close()
