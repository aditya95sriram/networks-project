import socket, os
import signal
from time import sleep
from handlers import handle_client
from multiprocessing import Lock

try:
    man_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print "socket created successfully"
except socket.error as err:
    print "socket creating failed:", err
    
man_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # to avoid port already in use error
    
port = 12345
man_sock.bind(('',port))
print "socket binded to", port

man_sock.listen(5)
print "socket is listening"

def child_exited(sig, frame):   # to clean up completed child processes (if needed)
    print "recvd SIGCHILD, waiting for child ... "
    pid, exitcode = os.wait()
    print "Child process {pid} exited with code {exitcode}".format(pid=pid, exitcode=exitcode)

signal.signal(signal.SIGCHLD, child_exited) # register child cleaner for SIGCHILD signal

os.chdir('server')  # change into root directory of server
cred_lock = Lock()
while True:
    try:
        client_ctrl_sock, client_addr = man_sock.accept()
    except socket.error as err:   # interrupted sys call when child exits
        if err.errno == 4: # interrupted sys call
            print "caugh interrupted sys call"
            continue
        else:
            raise
    childpid = os.fork()

    if childpid < 0:
        print "fork failed"
    elif childpid == 0: 
        print "process", os.getpid(), "assigned to client", client_addr
        handle_client(client_ctrl_sock, client_addr, cred_lock)
        break
    else:
        continue
print "outside"        
