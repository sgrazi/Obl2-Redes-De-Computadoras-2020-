import socket
from threading import Lock 

mutexTelnet=Lock()


masterTelnet = socket.socket()
masterTelnet.bind(("", 2025))
masterTelnet.listen()
sktTelnet,addr =masterTelnet.accept()
comando=b''
char=b''
while 1:
    char =sktTelnet.recv(10)
    comando+=char
    if char.decode("unicode_escape")=="\r\n":
        retorno="Recibido: ".encode("unicode_escape")+comando
        sktTelnet.sendall(retorno)
        comando=b''
        char=b''


