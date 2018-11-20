import socket, os
from time import sleep
from multiprocessing import Lock
import pickle
from actions import *

def handle_client(ctrl_sock, addr, cred_lock):
    print "Got connection from", addr
    #print "client", ctrl_sock
    
    data_man_port = ctrl_sock.recv(1024)
    print "data man port recd", data_man_port
    
    data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while True: # try to connect to client data channel
        try:
            data_sock.connect( (addr[0], int(data_man_port) ))
            print "data channel established with", addr[0], "pid", os.getpid()
            break
        except socket.error as err:
            if err.errno == 111:  # connection refused
                #print "connection refused, trying again"
                continue
            else: raise
    
    cur_user = ""
    while True: # process commands from client
        command = ctrl_sock.recv(1024).strip().split("#")
        comm_name = command[0]
        comm_args = command[1:]
        
        if comm_name == "signup":
            res = server_signup(ctrl_sock, data_sock, comm_args, cred_lock)
            if res:  cur_user = comm_args[0]
        elif comm_name == "signin":
            res = server_signin(ctrl_sock, data_sock, comm_args)
            if res: cur_user = comm_args[0]
        elif comm_name == "signout":
            server_signout(ctrl_sock, data_sock)
            cur_user = ""
        elif comm_name == "list":
            server_list(ctrl_sock, data_sock)
        elif comm_name == "delete":
            server_delete(ctrl_sock, data_sock, comm_args, cur_user, addr[0])
        elif comm_name == "download":
            server_download(ctrl_sock, data_sock, comm_args, cur_user, addr[0])
        elif comm_name == "upload":
            server_upload(ctrl_sock, data_sock, comm_args, cur_user, addr[0])
        else:
            print "connection closed by", addr
            print "terminating assigned process", os.getpid()
            break
 
    print "sleep start"
    sleep(1)
    print "sleep end"
    #data_sock.send("closing")
    ctrl_sock.close()
    data_sock.close()
    print "closed", addr
    #os._exit(0)
