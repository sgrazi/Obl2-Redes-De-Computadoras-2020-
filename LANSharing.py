import socket
import time
import struct #para obtener la ip de Hamachi
#import fcntl    #para obtener la ip de Hamachi
import math
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
tamDeBloque=256*1000
#Posiciones en los diccionarios
Seeders=1
seleccion = {} #lista para descargar disponibles

acceptedPieces=0 #variable paraz coordinar entre hilos las piezas aceptadas
dirStefa="25.96.130.128"
dirFran= "25.92.62.202"
dirMartin= "25.91.200.244"
dirBroadcast= "25.255.255.255" #Broadcast de Hamachi, el real es 255.255.255.255

def aceptarDescarga(md5,start,size,sktDescarga): #llamado por recibirSolicitudesDeDescarga, acepta solicitud de descarga y la envia
    mutexLocales.acquire() #mutuoexcluimos archivosLocales
    filePath =os.getcwd()+os.sep+'Archivos'+os.sep+archivosLocales[md5][0]
    mutexLocales.release() #liberamos archivosLocales
    fileSize = os.path.getsize(filePath)
    if os.path.isfile(filePath): #Si existe el archivo
        if start>=0 and size>0 and start+size<fileSize and size<fileSize :
            with open(filePath, "rb") as f:
                f.seek(start, 0)
                piece = f.read(size)
                piece = "DOWNLOAD OK\n".encode() + piece
        else:
            piece = "DOWNLOAD FAILURE\nBAD REQUEST\n".encode()
    else:
        piece = "DOWNLOAD FAILURE\nMISSING\n".encode()

    sktDescarga.sendall(piece)  
    #print("la mando")
    sktDescarga.close()

def recibirDescarga(sktSeeder,offset,totalSize,pathfile): #llamado por verCompartidos para descargar
    #se espera un DOWNLOAD OK\n, seguido de el bloque, (retorna en bytes)
    buf = b''
    global acceptedPieces
    #print("iniciando descarga")
    while totalSize:
        #print("recibiendo pedazo")
        newbuf = sktSeeder.recv(totalSize)
        #print("recibido:"+str(len(newbuf))+"bytes")
        if not newbuf: #si no recibo más nada me voy (count>fileSize)
            break
        buf += newbuf
        totalSize -= len(newbuf)

    sktSeeder.close()
    if buf[0:len("DOWNLOAD OK\n")].decode() == 'DOWNLOAD OK\n' and acceptedPieces>=0: #nos llegó bien y por ahora no hay errores
        buf=buf[12:] #stripeamos download ok
        acceptedPieces+=1
        mutexArchivo.acquire()
        with open(pathfile, "wb") as f:
            f.seek(offset, 0)
            f.write(buf)
            f.close()
        mutexArchivo.release()
        

    if buf[0:len("DOWNLOAD FAILURE\n")].decode() == 'DOWNLOAD FAILURE\n': #nos llegó mal por
        acceptedPieces=-1
        sendTelnetResponse(buf[len("DOWNLOAD FAILURE\n"):].decode())
        #print("error en descarga")
    
   

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
    global seleccion
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
        print(seleccion)
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
        if addr[0]!=socket.gethostbyname(dirMartin) or addr[0]!=socket.gethostbyname(socket.gethostname()): #no queremos escuchar nuestros propios mensajes en hamachi ni socket.gethostname()
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
                        archivosDeRed[datos[fileMd5]]=[int(datos[fileSize]),{addr[0]:[datos[fileName],3]}]
                    mutexRed.release()

        if(lineas[0]=="REQUEST"):
            anuncio=generarAnuncio()
            scktAnuncio = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            scktAnuncio.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            time.sleep(random.uniform(0,5))
            scktAnuncio.sendto((anuncio).encode(),(dirBroadcast,2020))
    
      


def verCompartidos(): #invocado por el usuario con el comando 1, para ver los archivos disponibles a descarga y descargarlos
    sendTelnetResponse("Disponibles en la red para descargar:")
    sendTelnetResponse("fileID - fielSize fileName1 fileName2 fileName3 ....")
    global seleccion
    seleccion={}
    i=0
    nombresExistentes=[] #para no repetir los nombres de archivo con distintos seeders
    mutexRed.acquire()
    nombres=""
    for archivo in archivosDeRed: #archivo=MD5=key
        seleccion[i]=archivo
        nombres=""
        for IP in archivosDeRed[archivo][Seeders]: #listamos todos los nombres DISTINTOS del archivo
            nombre=archivosDeRed[archivo][Seeders][IP][fileName]
            if(nombre not in nombresExistentes): #Verificamos que sean distintos
                nombres=nombres+nombre+" "
                nombresExistentes.append(nombre)
        sendTelnetResponse(str(i)+" - "+str(archivosDeRed[archivo][0])+" "+nombres) #0=fileSize
        nombresExistentes.clear()    
        i+=1
    mutexRed.release()

def getFile(nroArchivo):
    if nroArchivo.isdigit():
        global seleccion
        if int(nroArchivo) in seleccion:
            selectedFileMd5=seleccion[int(nroArchivo)]
            sendTelnetResponse("---Enviando Anuncio de descarga----")
            #se tendría que iterar entre seeders
           
            mutexRed.acquire()
            tamArchivo=archivosDeRed[selectedFileMd5][0] #0=fileSize
            #creamos el archivo vacío
            sendTelnetResponse("Ingrese nombre y extensión para el archivo a descargar:")
            nombreDelArchivoNuevo=getTelnetCommand()
            pathfile = os.getcwd()+os.sep+'Archivos'+os.sep+nombreDelArchivoNuevo
            with open(pathfile,"wb+") as f: # open for [w]riting as [b]inary
                f.seek(tamArchivo-1)
                f.write(b"\0")#encode lo pasa a bytes
                f.close()

            cantPieces=len(archivosDeRed[selectedFileMd5][Seeders]) #se le pedirá un pedazo a cada seeder
            tamPieces=math.floor(tamArchivo/cantPieces)
            #sendTelnetResponse("tamaño de pieza : "+str(tamPieces))
            offset = 0
            global acceptedPieces
            for IP in archivosDeRed[selectedFileMd5][Seeders]: # IP=key   
                if(IP==len(archivosDeRed[selectedFileMd5][Seeders])-1): #es el último seeder, le corresponde una pieza más grande generalmente
                    tamPieces=tamPieces+ (tamPieces % cantPieces )
                    #sendTelnetResponse("tamaño de pieza final : "+str(tamPieces))
                anuncioDescarga = "DOWNLOAD\n"+str(selectedFileMd5)+"\n"+ str(offset) +"\n"+str(tamPieces)+"\n" #start=0 size=0 etapa de testing
                sktSeeder = socket.socket()
                #sendTelnetResponse("Intentando conectar con: "+str(IP) )
                sktSeeder.connect((str(IP),2020)) #que conecte en el puerto que pueda (en manos del SO)
                sktSeeder.send(anuncioDescarga.encode())
                try:
                    _thread.start_new_thread(recibirDescarga,(sktSeeder,offset,tamPieces+len("DOWNLOAD OK\n"),pathfile))#recibirDescarga guarda en el archivo  previamente creado
                except:
                    print ("Error: unable to start thread")
                    acceptedPieces=-1
                offset +=tamPieces

            mutexRed.release()   
            while(acceptedPieces!=cantPieces):
                if(acceptedPieces==-1):
                    sendTelnetResponse(" --- Ocurrió un error en alguna descarga --- ")
                    os.remove(pathfile)

            sendTelnetResponse(" --- Fin de descarga --- ") 
            ofrecer(nombreDelArchivoNuevo)
            acceptedPieces=0
        else:
            sendTelnetResponse("No existe ese fileID, liste de nuevo")
    else:
        sendTelnetResponse("No se recibió un dígito como input, volviendo al menú")



def ofrecer(nombreA): #añade un archivo local a los announce
    pathToFile=os.getcwd()+os.sep+'Archivos'+os.sep+nombreA
    if(os.path.isfile(pathToFile)):
        archivosLocales[md5(pathToFile)] = [nombreA,os.path.getsize(pathToFile)]

def getTelnetCommand():
    char =sktTelnet.recv(1)
    comando=char.decode("unicode_escape")
    while 1:
        char =sktTelnet.recv(1)
        if char.decode("unicode_escape")=="\n":
            print ("comando:"+comando[:-1]+":")
            return comando[:-1] #sacamos el \r
        comando+=char.decode("unicode_escape")
            

def sendTelnetResponse(msg): #msg es un String
        retorno=msg.encode()+"\r\n".encode()
        sktTelnet.sendall(retorno) 



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
    mutexArchivo = Lock()
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

    #telnet socket
    masterTelnet = socket.socket()
    masterTelnet.bind(("", 2025))
    masterTelnet.listen()
    

    salir = False
    while 1: #ES UN DAEMON
        sktTelnet,addr =masterTelnet.accept()
        negociacionTelnet =sktTelnet.recv(100)
        salir=False

        sendTelnetResponse("     ______                           __     _______            ")
        sendTelnetResponse("    /_  __/___  _____________  ____  / /_   / ____(_)___  ____ _")
        sendTelnetResponse("     / / / __ \/ ___/ ___/ _ \/ __ \/ __/  / /_  / / __ \/ __ `/")
        sendTelnetResponse("    / / / /_/ / /  / /  /  __/ / / / /_   / __/ / / / / / /_/ / ")
        sendTelnetResponse("   /_/  \____/_/  /_/   \___/_/ /_/\__/  /_/   /_/_/ /_/\__, / " )
        sendTelnetResponse("                                                       /____/  ®")
        sendTelnetResponse("Bienvenido a TorrentFing ingrese alguno de los siguientes comandos :\n")
        #Request inicial de conexión
        scktAnuncio.sendto(("REQUEST\n").encode(),(dirBroadcast,2020))
        while (not salir):
            sendTelnetResponse("---- Comandos ----")
            sendTelnetResponse("- offer <filename>")
            sendTelnetResponse("- get <fileid>")
            sendTelnetResponse("- list")
            sendTelnetResponse("- exit")

            comando = getTelnetCommand()

            if (comando == "list"):
                verCompartidos()
            else:
                if (comando[0:len("get")] == "get"):
                    getFile(comando[len("get "):])
                else:
                    if (comando[0:len("offer")] == "offer"):
                        nombreA = comando[len("offer "):]
                        ofrecer(nombreA)
                    else:
                        if (comando == "exit"):
                            sktTelnet.close()
                            salir =True
                        else:
                            sendTelnetResponse("el comando \'"+comando+"\' no existe" )
        