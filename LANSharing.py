import socket
import time
import struct
import _thread 
import hashlib  #md5
import random   #espera aleatorea de tiempos
import os  #chequear que existe un archivo
import re #splitear los mensajes del protocolo separados por tabs y enters
from threading import Lock  #mutuoexcluir el acceso a estructuras de datos

#Posiciones en lo recibido por anuncios
fileName=0
ttl=1
fileSize=1
fileMd5=2

#tamaño de bloquen de distribución 256kb
tamDeBloque=15
#Posiciones en los diccionarios
Seeders=1

dirStefa="25.96.130.128"
dirFran= "25.92.62.202"
dirMartin= "25.91.200.244"
dirBroadcast= "25.255.255.255" #Broadcast de Hamachi, el real es 255.255.255.255

def aceptarDescarga(md5,start,size,sktDescarga): #llamado por recibirSolicitudesDeDescarga, acepta solicitud de descarga y la envia
    mutexLocales.acquire() #mutuoexcluimos archivosLocales
    filePath ='Archivos/'+archivosLocales[md5][0]
    mutexLocales.release() #liberamos archivosLocales
    with open(filePath, "rb") as f:
        f.seek(start, 0)
        piece = f.read(size)
        piece = "DOWNLOAD OK\n".encode() + piece
        sktDescarga.sendall(piece)  
        print("la mando")
        sktDescarga.close()

def recibirDescarga(sock,count): #llamado por verCompartidos para descargar
    #se espera un DOWNLOAD OK\n, seguido de el bloque, (retorna en bytes)
    buf = b''
    print("iniciando descarga")
    while count:
        print("recibiendo pedazo")
        newbuf = sock.recv(count)
        print("recibido:"+str(len(newbuf))+"bytes")
        if not newbuf: #si no recibo más nada me voy (count>fileSize)
            break
        buf += newbuf
        count -= len(newbuf)
    return buf.decode()

def md5(fPath): #crea el id para el file
    hash_md5 = hashlib.md5()
    with open(fPath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def generarAnuncio(): #genera a un anuncio, lo llama enviarAnuncios
    anuncio = "ANNOUNCE\n"
    mutexLocales.acquire() #mutuoexcluimos archivosLocales
    for key in archivosLocales:
        anuncio += archivosLocales[key][0] + "\t" + str(archivosLocales[key][1]) + "\t" + str(key) +"\n"
    mutexLocales.release() #liberamos archivosLocales
    return anuncio


def enviarAnuncios(scktAnuncio): #hilo permanente que envia anuncios de archivos locales
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

def recibirSolicitudesDeDescargas(scktEscucha): #hilo permanente que recibe solicitudes de descarga
    scktEscucha.listen()
    while True:
        cliente,addr =scktEscucha.accept()
        print("solicitud de conexion de:"+addr[0])
        mensaje = cliente.recv(1024) #escucha con un buffer de 1024bytes(1024 chars) en el 2020
        lineas=["SinLectura"]
        if(addr[0]!=socket.gethostbyname(dirMartin)): #no queremos escuchar nuestros propios mensajes en hamachi
            lineas=re.split(r'\n+', mensaje.decode())

        if(lineas[0]=="DOWNLOAD"):
            print("solicitud de descarga de:"+addr[0]+"del archivoMD5:"+lineas[1])

            try:
                _thread.start_new_thread(aceptarDescarga,(lineas[1],int(lineas[2]),int(lineas[3]),cliente))
            except:
                print ("Error: unable to start thread")
           

def recibirAnuncios(scktEscucha): #hilo permanente que recibe anuncios de archivos
    while True:
        mensaje,addr = scktEscucha.recvfrom(1024) #escucha con un buffer de 1024bytes(1024 chars) en el 2020
        lineas=["SinLectura"]
        #if(addr[0]!=socket.gethostbyname(dirStefa)): #no queremos escuchar nuestros propios mensajes en hamachi
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
    
      


def verCompartidos(): #invocado por el usuario con el comando 1, para ver los archivos disponibles a descarga y descargarlos
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
            offset = 0
            archivoData=""
            mutexRed.acquire()
            while len(archivoData) != int(archivosDeRed[selectedFileMd5][0]): #0 es tamaño
                #print(f'{len(archivoData)}--{archivosDeRed[selectedFileMd5][0]}')
                for IP in archivosDeRed[selectedFileMd5][Seeders]: # IP=key     
                    anuncioDescarga = "DOWNLOAD\n"+str(selectedFileMd5)+"\n"+ str(offset) +"\n"+str(tamDeBloque)+"\n" #start=0 size=0 etapa de testing
                    sktSeeder = socket.socket()
                    print("Intentando conectar con: "+str(IP) )
                    sktSeeder.connect((str(IP),2020)) #que conecte en el puerto que pueda (en manos del SO)
                    sktSeeder.send(anuncioDescarga.encode())
                    recibido = str(recibirDescarga(sktSeeder,tamDeBloque))#llega decodificado
                    sktSeeder.close()
                    if recibido[0:12] == 'DOWNLOAD OK\n':
                        archivoData+=recibido[12:]
                        offset = len(archivoData)
                        print(f'{archivoData}')


            mutexRed.release()


            print("Msg recibido: "+archivoData)
            print("Data del archivo: "+archivoData+"   ")
            mutexRed.acquire()
            print("Nombre para el archivo descargado junto a su extensión:")
            nombreDelArchivoNuevo=input()
            #tam=archivosDeRed[selectedFileMd5][fileSize]
            mutexRed.release()
            pathfile = os.getcwd()+'\\Archivos\\'+nombreDelArchivoNuevo
            with open(pathfile,"wb+") as file: # open for [w]riting as [b]inary
                file.write(archivoData.encode()) #encode lo pasa a bytes
                file.close()
            #falta agregar el archivo nuevo a archivos locales automaticamente(por letra)
           


def ofrecer(nombreA): #añade un archivo local a los announce
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