import socket
import time
import _thread 
import hashlib  #md5
import random   #espera aleatorea de tiempos
import os.path  #chequear que existe un archivo
import re #splitear los mensajes del protocolo separados por tabs y enters
from threading import Lock  #mutuoexcluir el acceso a estructuras de datos

#Posiciones en lo recibido por anuncios
fileName=0
fileSize=1
fileMd5=2

#Posiciones en los diccionarios
Seeders=2
ttls=3


dirFran= "25.92.62.202"
dirMartin= "25.91.200.244"
dirBroadcast= "25.255.255.255" #Broadcast de Hamachi, el real es 255.255.255.255

def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def enviarAnuncios(scktAnuncio):
    while True:
        time.sleep(5)
        time.sleep(random.uniform(0.5,1))
        print(archivosDeRed)
        if( bool(archivosLocales)): #archivosLocales no vacíos
            anuncio = "ANNOUNCE\n"
            mutexLocales.acquire() #mutuoexcluimos archivosLocales
            for key in archivosLocales:
                anuncio += archivosLocales[key][0] + "\t" + str(archivosLocales[key][1]) + "\t" + str(key) +"\n"
            mutexLocales.release() #liberamos archivosLocales
            scktAnuncio.sendto((anuncio).encode(),(dirBroadcast,2020))
            

def recibirAnuncios(scktEscucha):
    while True:
        mensaje,addr = scktEscucha.recvfrom(1024) #escucha con un buffer de 1024bytes(1024 chars) en el 2020
        #if(addr==socket.gethostbyname("localhost")): #no queremos escuchar nuestro propio broadcast
        lineas=re.split(r'\n+', mensaje.decode())

        if(lineas[0]=="ANNOUNCE"):
            iterLinea = iter(lineas)
            next(iterLinea)
            for linea in iterLinea:
                datos=re.split(r'\t+', linea)
                #print("causa de error:"+str(datos))
                if( datos[0]!=''): # para evitar la última linea que viene vacía
                    mutexRed.acquire() 
                    if( datos[fileMd5] in archivosDeRed): #sólo debemos agregar el nuevo seeder
                        if(not (addr[0] in archivosDeRed[datos[fileMd5]][Seeders]) ): # efectivamente es nuevo
                            archivosDeRed[datos[fileMd5]][Seeders].append(addr[0])
                            archivosDeRed[datos[fileMd5]][ttls].append(3) 
                        else: #seeder conocido, corresponde actualizar su ttl
                            indexSeeder=archivosDeRed[datos[fileMd5]][Seeders].index(addr[0])
                            archivosDeRed[datos[fileMd5]][ttls][indexSeeder]=3
                    else:#agregar nuevo archivo
                        archivosDeRed[datos[fileMd5]]=[datos[fileName],datos[fileSize],[addr[0]],[3]]
                    mutexRed.release()



        if(lineas[0]=="REQUEST"):
            print("retornar request")



def verCompartidos():
    print("Disponibles en la red para descargar:")

def ofrecer():
    print("Indique nombre del archivo que desea ofrecer:\n")
    nombreA = input()

    if(os.path.isfile('./Archivos/'+nombreA)):
        archivosLocales[md5('Archivos/'+nombreA)] = [nombreA,os.path.getsize('./Archivos/'+nombreA)]




if __name__ == '__main__':
    
    #socketAnunciar
    scktAnuncio = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    scktAnuncio.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    scktEscucha = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    scktEscucha.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    scktEscucha.bind(("", 2020))

    #archivos de Red
    archivosDeRed = {}  #md5 : nombre , tamaño, Seeders[], ttl[]
    mutexRed = Lock()
    #archivos locales
    archivosLocales = {} #md5 : nombre , tamaño 
    mutexLocales = Lock()

    try:
        _thread.start_new_thread(enviarAnuncios,(scktAnuncio, ))
        _thread.start_new_thread(recibirAnuncios,(scktEscucha, ))
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
            verCompartidos()
        else:
            if (accion == "2"):
                print(2)
            else:
                if (accion == "3"):
                    ofrecer()
                else:
                    salir = True