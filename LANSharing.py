import socket
import time
import struct
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

#tamaño de bloquen de distribución 256kb
tamDeBloque=10
#Posiciones en los diccionarios
Seeders=1

myIP="25.91.200.244"
dirFran= "25.92.62.202"
dirMartin= "25.91.200.244"
dirBroadcast= "25.255.255.255" #Broadcast de Hamachi, el real es 255.255.255.255

def aceptarDescarga(md5,start,size,sktDescarga):
    mutexLocales.acquire() #mutuoexcluimos archivosLocales
    filePath ='Archivos/'+archivosLocales[md5][0]
    mutexLocales.release() #liberamos archivosLocales

    with open(filePath, "rb") as f:
        f.seek(start, 0)    
        piece =f.read(size)    
        #  if piece == "":
        #      break # end of file
        sktDescarga.sendall(piece.encode())   

def recibirDescarga(sock,count): #se espera un DOWNLOAD OK\n, seguido de el bloque
    buf = b''
    while count:
        newbuf = sock.recv(count)
        if not newbuf: return None
        buf += newbuf
        count -= len(newbuf)
    buf = buf.split("\n")[1:]
    return buf

def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def generarAnuncio():
    anuncio = "ANNOUNCE\n"
    mutexLocales.acquire() #mutuoexcluimos archivosLocales
    for key in archivosLocales:
        anuncio += archivosLocales[key][0] + "\t" + str(archivosLocales[key][1]) + "\t" + str(key) +"\n"
    mutexLocales.release() #liberamos archivosLocales
    return anuncio


def enviarAnuncios(scktAnuncio):
    while True:
        time.sleep(10)#30 seg
        print("---------------anunciandooooo----------------")
        time.sleep(random.uniform(0.5,1))
       
        if( bool(archivosLocales)): #archivosLocales no vacíos
            anuncio=generarAnuncio()
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

def recibirSolicitudesDeDescargas(scktEscucha):
    scktEscucha.listen()
    while True:
        cliente,addr =scktEscucha.accept()
        print("solicitud de conexion de:"+addr[0])
        mensaje = cliente.recv(1024) #escucha con un buffer de 1024bytes(1024 chars) en el 2020
        lineas=["SinLectura"]
        if(addr[0]!=socket.gethostbyname(myIP)): #no queremos escuchar nuestros propios mensajes en hamachi
            lineas=re.split(r'\n+', mensaje.decode())

        if(lineas[0]=="DOWNLOAD"):
             print("solicitud de descarga de:"+addr[0]+"del archivoMD5:"+lineas[1]) 
            cliente = socket.socket()
            cliente.connect((addr[0],"")) #que conecte en el puerto que pueda (en manos del SO)
            try:
                _thread.start_new_thread(aceptarDescarga,(lineas[1],lineas[2]),lineas[3],cliente) 
            except:
                print ("Error: unable to start thread")
            cliente.close()
           

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
            anuncio=generarAnuncio()
            scktAnuncio = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            scktAnuncio.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            time.sleep(random.uniform(0,5))
            scktAnuncio.sendto((anuncio).encode(),(dirBroadcast,2020))
    
      


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
            selectedFileMd5=seleccion[int(nroArchivo)]
            print("---Enviando Anuncio de descarga----")
            #se tendría que iterar entre seeders
            anuncio = "DOWNLOAD\n"+str(selectedFileMd5)+"\n0\n"+str(tamDeBloque)+"\n" #start=0 size=0 etapa de testing
            archivoEnBytes=""
            mutexRed.acquire()
            #while not finished, keep looping1
            for IP in archivosDeRed[selectedFileMd5][Seeders]: # IP=key     
                sktSeeder = socket.socket()
                print("Intentando conectar con: "+str(IP) )
                sktSeeder.connect((str(IP),2020)) #que conecte en el puerto que pueda (en manos del SO)
                sktSeeder.send(anuncio.encode())
                archivoEnBytes+=recibirDescarga(sktSeeder,tamDeBloque)
                sktSeeder.close()
            mutexRed.release()

            mutexRed.acquire()
            nombreDelArchivoNuevo=archivosDeRed[selectedFileMd5][fileName]
            #tam=archivosDeRed[selectedFileMd5][fileSize]
            mutexRed.acquire()
            out_file = open(nombreDelArchivoNuevo, "wb") # open for [w]riting as [b]inary
            out_file.write(archivoEnBytes)
            out_file.close()
            #falta agregar el archivo nuevo a archivos locales automaticamente(por letra)
           


def ofrecer(nombreA):
    if(os.path.isfile('./Archivos/'+nombreA)):
        archivosLocales[md5('Archivos/'+nombreA)] = [nombreA,os.path.getsize('./Archivos/'+nombreA)]




  



if __name__ == '__main__':
    
    #socketAnunciar
    scktAnuncio = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    scktAnuncio.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    scktEscuchaUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    scktEscuchaUDP.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    scktEscuchaUDP.bind(("", 2020))

    scktEscuchaTCP = socket.socket()
    scktEscuchaTCP.bind(("", 2020))

    #archivos de Red
    archivosDeRed = {}  #md5 : tamaño, {Seeders: FileName,ttl}
    mutexRed = Lock()
    #archivos locales
    archivosLocales = {} #md5 : FileName , tamaño 
    mutexLocales = Lock()

    #Request inicial
    scktAnuncio.sendto(("REQUEST\n").encode(),(dirBroadcast,2020))
    
    try:
        _thread.start_new_thread(recibirSolicitudesDeDescargas,(scktEscuchaTCP, ))
        _thread.start_new_thread(enviarAnuncios,(scktAnuncio, ))
        _thread.start_new_thread(recibirAnuncios,(scktEscuchaUDP, ))
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