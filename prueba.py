import socket
#import fcntl
import struct #para obtener la ip de Hamachi


from threading import Lock 

mutexTelnet=Lock()


"""def get_ip_address(ifname): #nombre de la interfaz
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])"""

masterTelnet = socket.socket()
masterTelnet.bind(("", 2025))
masterTelnet.listen()
#print(socket.gethostbyname(socket.gethostname()))
sktTelnet,addr =masterTelnet.accept()
comando=b''
char=b''
while 1:
    char =sktTelnet.recv(2)
    comando+=char
    if char.decode("unicode_escape")=="\r\n":
        retorno="Recibido: ".encode("unicode_escape")+comando
        sktTelnet.sendall(retorno)
        comando=b''
        char=b''



