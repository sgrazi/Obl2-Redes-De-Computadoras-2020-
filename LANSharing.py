import socket
import time
import _thread
import hashlib
import random
import os.path

#MODIFICO MARTIN

dirFran= "25.92.62.202"
dirMartin= "25.91.200.244"
dirBroadcast= "25.255.255.255" #Broadcast de Hamachi, el real es 255.255.255.255

def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def anuncio(scktAnuncio):
    while True:
        time.sleep(30)
        time.sleep(random.uniform(0.5,1))
        anuncio = "ANNOUNCE\n"
        for key in archivosDisponibles:
            anuncio += archivosDisponibles[key][0] + "\t" + str(archivosDisponibles[key][1]) + "\t" + str(key) +"\n"
        scktAnuncio.sendto((anuncio).encode(),(dirBroadcast,2020))

def ofrecer():
    print("Indique nombre del archivo que desea ofrecer:\n")
    nombreA = input()
    if(os.path.isfile('./Archivos/'+nombreA)):
        archivosDisponibles[md5('Archivos/'+nombreA)] = [nombreA,os.path.getsize('./Archivos/'+nombreA)]


if __name__ == '__main__':
    
    #socketAnunciar
    scktAnuncio = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    scktAnuncio.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    #archivos locales
    archivosDisponibles = {}

    try:
        _thread.start_new_thread(anuncio,(scktAnuncio, ))
    except:
        print ("Error: unable to start thread")

    salir = False
    while (not salir):

        print("Bienvenido a TorrentFing")
        print("1-Ver archivos disponibles")
        print("2-Descargar archivo")
        print("3-Compartir archivo")
        print("--Cualquier otra cosa para salir---")

        accion = input()

        if (accion == "1"):
            print(1)
        else:
            if (accion == "2"):
                print(2)
            else:
                if (accion == "3"):
                    ofrecer()
                else:
                    salir = True