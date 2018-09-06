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

# Used for testing loopback without bluetooth.
SERVER_IP_PORT=8003
SERVER_IP_BIND_ADDRESS="0.0.0.0"

# 
SERVER_BLUETOOTH_PORT=0x1003


PACKET_SIZE=512

LOCAL_SSH_PORT=22
LOCAL_SSH_ADDRESS="127.0.0.1"

VERBOSE=False

################################################################################
#
################################################################################

def serverDataFromLocal(localSshSocket, clientSocket):
   """thread worker function"""
   if VERBOSE:
      print 'Server (local SSH-->client): Thread starting'

   while True:
      # Wait for and get data from local SSH server.
      dataFromLocalSsh = localSshSocket.recv(PACKET_SIZE)

      if dataFromLocalSsh == "":
         if VERBOSE:
            print "Server (local SSH-->client): Data from local looks empty."

         # The local SSH server has disconnected, we don't need a connection to
         # the Client anymore, so we neatly shut it down.
         clientSocket.shutdown(socket.SHUT_RDWR)
         return

      # Send data from the local SSH connection to client.
      clientSocket.sendall(dataFromLocalSsh)
       
   return

################################################################################
#
################################################################################

def serverDataToLocal(clientSocket, localSshSocket):
   """thread worker function"""
   if VERBOSE:
      print 'Server (client --> local SSH): Thread starting'

   while True:
      # Wait for and get data from client.
      dataFromClient = clientSocket.recv(PACKET_SIZE)

      if dataFromClient == "":
         if VERBOSE:
            print "Server (client -->local SSH): Data to local looks empty."

         # The Bluetooth client has disconnected, so we don't need a connection
         # to local SSH server anymore, so we neatly shut it down.
         localSshSocket.shutdown(socket.SHUT_RDWR)
         return

      # Send data from Client to the local SSH connection.
      localSshSocket.sendall(dataFromClient)
       
   return

################################################################################
#
################################################################################

if BLUETOOTH:
   serverRemoteSocket = bluetooth.BluetoothSocket(bluetooth.L2CAP)
   serverRemoteSocket.bind(("",SERVER_BLUETOOTH_PORT))
   serverRemoteSocket.listen(1)
else:
   # Socket that server will listen with for clients.
   serverRemoteSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

   # Bind the remote socket to our port.
   serverRemoteSocket.bind((SERVER_IP_BIND_ADDRESS, SERVER_IP_PORT))

   # Listen for a connection, this is a private link so expect only one connection.
   serverRemoteSocket.listen(1)

   print "Server is listening for Client on on port:", SERVER_IP_PORT


while True:
   print "Server is listening for Client:"

   # Wait for Server to receive a connection from a Client .
   (clientSocket, address) = serverRemoteSocket.accept()

   # Display socket and address of Client  that is connecting to us.
   print "Contacted by", address, "@", time.asctime()

   try:
      # Make a connection to the local SSH client.
      serverLocalSshSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      serverLocalSshSocket.connect((LOCAL_SSH_ADDRESS, LOCAL_SSH_PORT))

      # Thread for receiving data from Client then sending it on to local SSH.
      serverDataToLocalThread = threading.Thread(target=serverDataToLocal,
                                                 args=(clientSocket,
                                                       serverLocalSshSocket))

      # Thread for receiving data from local SSH then sending it on to Client.
      serverDataFromLocalThread  = threading.Thread(target=serverDataFromLocal,
                                                    args=(serverLocalSshSocket,
                                                          clientSocket))

      # Start the transfer threads.
      serverDataFromLocalThread.start()
      serverDataToLocalThread.start()

      # Wait for our threads to end.
      serverDataFromLocalThread.join()
      serverDataToLocalThread.join()

      # Close this connection the local SSH server.  We'll make a new one next
      # time a client connects.
      serverLocalSshSocket.close()

   except:
      print "something went wrong"
      pass

   print "Finished serving that Client @", time.asctime()


# EOF - l2cap_ssh_server.py
