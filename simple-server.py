import os
import signal
import socket
from multiprocessing import Lock, Process, Manager
from time import sleep
from actions import Server


def handle_client(ctrl_sock, addr, cred_lock, file_lock, file_list):
    print "Got connection from", addr
    # print "client", ctrl_sock

    data_man_port = ctrl_sock.recv(1024)
    print "data man port recd", data_man_port

    data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while True:  # try to connect to client data channel
        try:
            data_sock.connect((addr[0], int(data_man_port)))
            print "data channel established with", addr[0], "pid", os.getpid()
            break
        except socket.error as err:
            if err.errno == 111:  # connection refused
                # print "connection refused, trying again"
                continue
            else:
                raise
    server = Server(ctrl_sock, data_sock, addr[0], cred_lock)

    while True:  # process commands from client
        command = ctrl_sock.recv(1024).strip().split("#")
        comm_name = command[0]
        comm_args = command[1:]

        if comm_name == "signup":
            server.signup(comm_args)
        elif comm_name == "signin":
            server.signin(comm_args)
        elif comm_name == "signout":
            server.signout()
        elif comm_name == "list":
            server.list()
        elif comm_name == "delete":
            server.delete(comm_args)
        elif comm_name == "download":
            server.download(comm_args)
        elif comm_name == "upload":
            server.upload(comm_args)
        elif comm_name == "share":
            server.share(comm_args)
        elif comm_name == "showlog":
            server.showlog()
        else:
            print "connection closed by", addr
            print "terminating assigned process", os.getpid()
            break

    print "sleep start"
    sleep(1)
    print "sleep end"
    ctrl_sock.close()
    data_sock.close()
    print "closed", addr


try:
    man_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print "socket created successfully"
except socket.error as err:
    print "socket creating failed:", err
    raise

man_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # to avoid port already in use error
port = 12345
man_sock.bind(('', port))

print "socket binded to", port
man_sock.listen(5)

print "socket is listening"


def child_exited(sig, frame):   # to clean up completed child processes (if needed)
    print "recvd SIGCHILD, waiting for child ... "
    pid, exitcode = os.wait()
    print "Child process {pid} exited with code {exitcode}".format(pid=pid, exitcode=exitcode)


signal.signal(signal.SIGCHLD, child_exited)  # register child cleaner for SIGCHILD signal

os.chdir('server')  # change into root directory of server
manager = Manager()
file_list = manager.list()
cred_lock = Lock()
file_lock = Lock()
while True:
    try:
        client_ctrl_sock, client_addr = man_sock.accept()
    except socket.error as err:   # interrupted sys call when child exits
        if err.errno == 4:  # interrupted sys call
            print "caught interrupted sys call"
            continue
        else:
            raise
    cp = Process(target=handle_client, args=(client_ctrl_sock, client_addr, cred_lock, file_lock, file_list))
    cp.start()
print "outside"

