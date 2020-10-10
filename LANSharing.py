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
ttl=1
fileSize=1
fileMd5=2

#Posiciones en los diccionarios
Seeders=1

myIP="25.91.200.244"
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
        time.sleep(5)#30 seg
        time.sleep(random.uniform(0.5,1))
       
        if( bool(archivosLocales)): #archivosLocales no vacíos
            anuncio = "ANNOUNCE\n"
            mutexLocales.acquire() #mutuoexcluimos archivosLocales
            for key in archivosLocales:
                anuncio += archivosLocales[key][0] + "\t" + str(archivosLocales[key][1]) + "\t" + str(key) +"\n"
            mutexLocales.release() #liberamos archivosLocales
            scktAnuncio.sendto((anuncio).encode(),(dirBroadcast,2020))
        #Actualización TTL
        mutexRed.acquire() 
        print(archivosDeRed)
        seedersABorrar=[]
        archivosABorrar=[]
        for archivo in archivosDeRed: #archivo=MD5=key
            for IP in archivosDeRed[archivo][Seeders]: # IP=key
                if(archivosDeRed[archivo][Seeders][IP][ttl]>1): #Value=TTL
                    archivosDeRed[archivo][Seeders][IP][ttl]=archivosDeRed[archivo][Seeders][IP][ttl]-1
                else: #Se borra el seeder puesto no emitió por más de 90 segundos
                    seedersABorrar.append(IP)
                #del archivosDeRed[archivo][Seeders][IP]
                if(len(archivosDeRed[archivo][Seeders])==len(seedersABorrar)): #Se eliminó el último seeder del archivo, corresponde sacarlo de la lista
                    archivosABorrar.append(archivo)
                    #del archivosDeRed[archivo]
            for IP in seedersABorrar:
                del archivosDeRed[archivo][Seeders][IP]
            seedersABorrar.clear()
        for archivo in archivosABorrar:
            del archivosDeRed[archivo]
        archivosABorrar.clear()

        mutexRed.release()

def recibirAnuncios(scktEscucha):
    while True:
        mensaje,addr = scktEscucha.recvfrom(1024) #escucha con un buffer de 1024bytes(1024 chars) en el 2020
        lineas=["SinLectura"]
        #if(addr[0]!=socket.gethostbyname(myIP)): #no queremos escuchar nuestros propios mensajes en hamachi
        lineas=re.split(r'\n+', mensaje.decode())

        if(lineas[0]=="ANNOUNCE"):
            iterLinea = iter(lineas)
            next(iterLinea)
            for linea in iterLinea:
                datos=re.split(r'\t+', linea)
                #print("causa de error:"+str(datos))
                if( datos[0]!=''): # para evitar la última linea que viene vacía
                    mutexRed.acquire() 
                    if( datos[fileMd5] in archivosDeRed): #sólo debemos agregar/actualizar el nuevo/existente seeder (indiferente para el diccionario de seeders)
                        archivosDeRed[datos[fileMd5]][Seeders][addr[0]]=[datos[fileName],3] #addr[0]=dirIP y ttl=3   
                    else:#agregar nuevo archivo
                        archivosDeRed[datos[fileMd5]]=[datos[fileSize],{addr[0]:[datos[fileName],3]}]
                    mutexRed.release()

        if(lineas[0]=="REQUEST"):
            print("retornar request")

        if(lineas[0]=="DOWNLOAD"): 
            sktDescarga = socket.socket()
            sktDescarga.connect(addr[0],0) #que conecte en el puerto que pueda (en manos del SO)
            try:
                _thread.start_new_thread(enviarAnuncios,(scktAnuncio, ))
                _thread.start_new_thread(recibirAnuncios,(scktEscucha, ))
            except:
                print ("Error: unable to start thread")
           


def verCompartidos():
    print("Disponibles en la red para descargar:")
    print("fileID - fielSize fileName1 fileName2 fileName3 ....")
    seleccion={}
    i=0
    nombresExistentes=[] #para no repetir los nombres de archivo con distintos seeders
    mutexRed.acquire()
    for archivo in archivosDeRed: #archivo=MD5=key
        seleccion[i]=archivo
        print(str(i)+" - "+str(archivosDeRed[archivo][0])+" ",end="") #0=fileSize
        for IP in archivosDeRed[archivo][Seeders]:
            nombre=archivosDeRed[archivo][Seeders][IP][fileName]
            if(nombre not in nombresExistentes):
                print(nombre,end=" ")
                nombresExistentes.append(nombre)
        nombresExistentes.clear()    
        print("")
        i+=1
   # if seleccion.
    mutexRed.release()
    print("Indique Nro del archivo que desea descargar.\nDe lo contrario ingrese cualuquier otra tecla para volver al menu")
    nroArchivo =input()
    if nroArchivo.isdigit():
        if int(nroArchivo) in seleccion:
            print("---DESCARGANDO----")
           


def ofrecer(nombreA):
    if(os.path.isfile('./Archivos/'+nombreA)):
        archivosLocales[md5('Archivos/'+nombreA)] = [nombreA,os.path.getsize('./Archivos/'+nombreA)]



def aceptarDescarga(md5,start,size,sktDescarga):
     while True:
        mensaje,addr = sktDescarga.recvfrom(1024) #escucha con un buffer de 1024bytes(1024 chars) en el 2020
        print("\""+mensaje.decode()+"\" desde la IP: "+addr[0]+" y puerto: "+addr[1])



if __name__ == '__main__':
    
    #socketAnunciar
    scktAnuncio = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    scktAnuncio.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    scktEscucha = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    scktEscucha.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    scktEscucha.bind(("", 2020))

    #archivos de Red
    archivosDeRed = {}  #md5 : tamaño, {Seeders: FileName,ttl}
    mutexRed = Lock()
    #archivos locales
    archivosLocales = {} #md5 : FileName , tamaño 
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
                    print("Indique nombre del archivo que desea ofrecer:\n")
                    nombreA = input()
                    ofrecer(nombreA)
                else:
                    salir = True