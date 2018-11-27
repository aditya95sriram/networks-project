import os
import random  # to generate port number
import socket
from time import sleep

from actions import Client, send_fix_msg

ctrl_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Define the port on which you want to connect
ctrl_man_port = 12345

# connect to the server
defaultip = "127.0.0.1"
if os.path.isfile("serverip.txt"):
    with open("serverip.txt", "r") as f: defaultip = f.read()

serverip = raw_input("Server IP addr:").strip()
if serverip:
    with open("serverip.txt", "w") as f: f.write(serverip)
else:
    serverip = defaultip
print "Connecting to server (%s)..."%(serverip)

    
ctrl_sock.connect((serverip, ctrl_man_port))
print "established control channel"

data_man_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

data_man_port = 54321
while True:
    try:
        print "trying to bind to", data_man_port
        data_man_sock.bind(('', data_man_port))
        break
    except socket.error as err:
        if err.errno == 98:  # address already in use
            data_man_port = random.randint(1000, 65000)
            continue
        else:
            raise

print "socket binded to data man port", data_man_port

send_fix_msg(ctrl_sock, str(data_man_port).zfill(5), 5)

print "sleep start"
sleep(1)
print "sleep end"

data_man_sock.listen(0)

data_sock, server_addr = data_man_sock.accept()
# data_man_sock.close/shutdown
print "established data channel with", server_addr, "pid", os.getpid()


def print_menu(d):
    print
    for item, itemnum in sorted(d.items(), key=lambda x: x[1]):
        print "{}: {}".format(itemnum, item)


menu1 = {"Sign up": 1, "Sign in": 2}
menu2 = {"List files": 1, "Upload file": 2, "Download file": 3, "Delete file": 4,
         "Share file": 5, "Show log": 6, "Sign out": 7}

client = Client(ctrl_sock, data_sock)

while True:
    # print "user:",client.user
    if client.user == "":
        print_menu(menu1)
        comm_id = raw_input("Your option:")
        if not comm_id.isdigit():
            print "invalid option"
            continue
        print
        comm_id = int(comm_id)
        if comm_id == menu1['Sign up']:  # signup
            client.signup()
        elif comm_id == menu1['Sign in']:  # signin
            client.signin()
        else:
            print "invalid option"
    else:
        print_menu(menu2)
        comm_id = raw_input("Your option:")
        if not comm_id.isdigit():
            print "invalid option"
            continue
        print
        comm_id = int(comm_id)
        if comm_id == menu2['List files']:  # list files
            client.list()
        elif comm_id == menu2['Upload file']:  # upload
            client.upload()
        elif comm_id == menu2['Download file']:  # download
            client.download()
        elif comm_id == menu2['Delete file']:  # delete
            client.delete()
        elif comm_id == menu2['Share file']:  # share file
            client.share()
        elif comm_id == menu2['Show log']:  # show log
            client.showlog()
        elif comm_id == menu2['Sign out']:  # sign out
            client.signout()
        else:
            print "invalid option"

