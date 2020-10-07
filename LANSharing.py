import socket
import time
import _thread
import hashlib
import random


#MODIFICO MARTIN

dirFran= "25.92.62.202"
dirMartin= "25.91.200.244"
dirBroadcast= "25.255.255.255" #Broadcast de Hamachi, el real es 255.255.255.255

def Anuncio(scktAnuncio):
    while True:
        time.sleep(1)
        time.sleep(random.uniform(0.5,1))
        #aca armar el string a enviar con el formato
        scktAnuncio.sendto(("Hola2").encode(),(dirMartin,2020))
        print("envie")


if __name__ == '__main__':
    scktAnuncio = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    scktAnuncio.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    try:
        _thread.start_new_thread(Anuncio,(scktAnuncio, ))
    except:
        print ("Error: unable to start thread")

    while 1:
        pass