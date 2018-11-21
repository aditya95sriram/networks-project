import socket, os
import random # to generate port number
from time import sleep
from getpass import getpass # to input password safely
from actions import *

ctrl_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Define the port on which you want to connect 
ctrl_man_port = 12345

# connect to the server on local computer
ctrl_sock.connect(('127.0.0.1', ctrl_man_port))
print "established control channel"

data_man_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

data_man_port = 54321
while True:
    try:
        print "trying to bind to", data_man_port
        data_man_sock.bind(('', data_man_port))
        break
    except socket.error as err:
        if err.errno == 98: # address already in use
            data_man_port = random.randint(1000, 65000)
            continue
        else: raise

print "socket binded to data man port", data_man_port

ctrl_sock.send(str(data_man_port))


print "sleep start"
sleep(1)
print "sleep end"

data_man_sock.listen(0)

data_sock, server_addr = data_man_sock.accept()
#data_man_sock.close/shutdown
print "established data channel with", server_addr, "pid", os.getpid()

#make_menu = lambda l: "\n".join("%d. %s"%e for e in zip(range(1,len(l)+1), l))
make_menu = lambda d: "\n".join("{1}: {0}".format(*e) for e in sorted(d.items(), key=lambda x:x[1]))
#menu1 = make_menu(["Sign up", "Sign in"])
menu1 = {"Sign up": 1, "Sign in": 2}
#menu2 = make_menu(["List files","Download file", "Delete file", "Sign out"])
menu2 = {"List files": 1, "Upload file": 2, "Download file": 3,"Delete file": 4, 
         "Share file": 5, "Show log": 6, "Sign out": 7}

cur_user = ""

while True:
    if cur_user == "":
        print make_menu(menu1)
        comm_id = raw_input("Your option:")
        if not comm_id.isdigit(): 
            print "invalid option"
            continue
        comm_id = int(comm_id)
        username = raw_input("Username:")
        #password = raw_input("Password (no special chars):")
        password = getpass()
        if comm_id == menu1['Sign up']: # signup
            res = client_signup(ctrl_sock, data_sock, username, password)
            if res: cur_user = username
        elif comm_id == menu1['Sign in']: # signin
            res = client_signin(ctrl_sock, data_sock, username, password)
            if res: cur_user = username
        else:
            print "invalid option"
    else:
        print make_menu(menu2)
        comm_id = raw_input("Your option:")
        if not comm_id.isdigit(): 
            print "invalid option"
            continue
        comm_id = int(comm_id)
        if comm_id == menu2['List files']: # list files
            client_list(ctrl_sock, data_sock)
        elif comm_id == menu2['Upload file']: # upload
            client_upload(ctrl_sock, data_sock)
        elif comm_id == menu2['Download file']: # download
            client_download(ctrl_sock, data_sock)
        elif comm_id == menu2['Delete file']: # delete
            client_delete(ctrl_sock, data_sock)
        elif comm_id == menu2['Share file']: # share file
            client_share(ctrl_sock, data_sock)
        elif comm_id == menu2['Show log']: # show log
            client_showlog(ctrl_sock, data_sock)
        elif comm_id == menu2['Sign out']: # sign out
            res = client_signout(ctrl_sock, data_sock)
            if res:
                cur_user = ""
        else:
            print "invalid option"
            
        

# receive data from the server 
#print "recd via ctrl sock", ctrl_sock.recv(1024)
#print "recd via data sock", data_sock.recv(1024)
# close the connection 
#s.close() 
