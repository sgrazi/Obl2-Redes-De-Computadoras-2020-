import socket

mi_socket = socket.socket()
mi_socket.bind(('25.93.171.86',2020))
mi_socket.listen(5)

while True:
    conexion, addr = mi_socket.accept()
    #modifiedMessage, addr = mi_socket.recvfrom(message.decode('utf-8'))
    print ("Nueva conexion establecida")
    print (addr)

    conexion.sendto(("Hola te saludo desde el servidor").encode(),('25.93.171.86', 2020))
    respuesta = conexion.recv(1024) #buffer
    print (respuesta.decode())

    #print(respuesta.decode())
    conexion.close()