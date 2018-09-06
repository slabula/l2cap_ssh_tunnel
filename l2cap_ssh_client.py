#! /usr/bin/python2

# Gordon McKillop <gordon.mckillop@gmail.com>
# Version 0.1.0 (2018-08-29)
#
# +--------------------------------------------------+
# | Host PC                                          |
# | +------------------+    +---------------------+  |
# | | Local SSH client |--->| l2cap_ssh_client.py |---------------+
# | +------------------+    +---------------------+  |            |
# +--------------------------------------------------+            |
#                                                             Bluetooth
# +--------------------------------------------------+            |
# | Raspberry Pi Zero W                              |            |
# | +------------------+    +---------------------+  |            |
# | | Local SSH server |<---| l2cap_ssh_server.py |<--------------+
# | +------------------+    +---------------------+  |
# +--------------------------------------------------+

import socket
import threading
import time

BLUETOOTH=True

if BLUETOOTH:
   import bluetooth

CLIENT_IP_PORT=8000

# Used for testing loopback without bluetooth.
SERVER_IP_PORT=8003
SERVER_IP_ADDRESS='127.0.0.1'

# 
SERVER_BLUETOOTH_PORT=0x1003
SERVER_BD_ADDRESS="B8:27:EB:EF:4E:33"

PACKET_SIZE=512

VERBOSE=False

################################################################################
#
################################################################################

def clientDataFromLocal(localSshSocket, serverSocket):
   """thread worker function"""
   if VERBOSE:
      print 'Client (local --> Server):'

   while True:
      # Wait for and get data from local SSH client.
      dataFromLocalSshClient = localSshSocket.recv(PACKET_SIZE)

      if dataFromLocalSshClient == "":
         if VERBOSE:
            print "Client (local --> Server): Data from local looks empty."

         # The local SSH client has disconnected, we don't need a connection to
         # Server anymore, so we neatly shut it down.
         serverSocket.shutdown(socket.SHUT_RDWR)
         return

      # Send data from the local SSH client to Server.
      serverSocket.sendall(dataFromLocalSshClient)
    
   return

################################################################################
#
################################################################################

def clientDataToLocal(serverSocket, localSshSocket):
   """thread worker function"""
   if VERBOSE:
      print 'Client (Server --> local):'

   while True:
      # Wait for and get data from local SSH server.
      dataFromServer = serverSocket.recv(PACKET_SIZE)

      if dataFromServer == "":
         if VERBOSE:
            print "Client (Server --> Local): Data from server looks empty."

         # The Server has disconnected, we don't need a connection to Local SSH
         # client anymore, so we neatly shut it down.
         localSshSocket.shutdown(socket.SHUT_RDWR)
         return

      # Send data Server to the local SSH client.
      localSshSocket.sendall(dataFromServer)
       
   return


################################################################################
#
################################################################################

clientLocalSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

clientLocalSocket.bind(('127.0.0.1', CLIENT_IP_PORT))

clientLocalSocket.listen(1)


while True:
   print "Client is listening on", CLIENT_IP_PORT

   # Wait for a SSH client connect to us.
   (sshClientSocket, address) = clientLocalSocket.accept()

   print "Contacted by", address, "@", time.asctime()



   try:
      if BLUETOOTH:
         print "Connecting to Server (via Bluetooth):"
         # Make a connection to the Scale Server via Bluetooth.
         serverSocket = bluetooth.BluetoothSocket(bluetooth.L2CAP)
         serverSocket.connect((SERVER_BD_ADDRESS, SERVER_BLUETOOTH_PORT))
      else:     
         print "Connecting to Server (via IP) on port:", SERVER_IP_PORT
         # Make a connection to the Server.
         serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
         serverSocket.connect((SERVER_IP_ADDRESS, SERVER_IP_PORT))


      # Thread that receives data from local SSH then sends it on to Server.
      clientDataFromLocalThread = threading.Thread(target=clientDataFromLocal,
                                                   args=(sshClientSocket,
                                                         serverSocket,))

      # Thread that received data from server then sends it on to local SSH.
      clientDataToLocalThread = threading.Thread(target=clientDataToLocal,
                                                 args=(serverSocket,
                                                       sshClientSocket,))

      # Start the sending and receiving threads.
      clientDataFromLocalThread.start()
      clientDataToLocalThread.start()

      # Wait for them to finish.  They will stop themselves when the connection
      # is no longer in use.
      clientDataFromLocalThread.join()
      clientDataToLocalThread.join()

      # Close this connection to Server.  We'll make a new one next time a
      # client connects to this client.
      serverSocket.close()
   except None:
      print "Client detected a problem."
      pass


   print "Finished serving that SSH client @", time.asctime()


# EOF - l2cap_ssh_client.py
