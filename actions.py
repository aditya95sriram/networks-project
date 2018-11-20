import socket, os
import pickle
import md5
import csv
from datetime import datetime

MAX_CHUNKS = 9999
CHUNK_SIZE = 1024

def read_cred():
    with open("credentials.db", "rb") as f:
        cred_dict = pickle.load(f)
    return cred_dict
    
def write_cred(cred_dict):
    with open("credentials.db", "wb") as f:
        pickle.dump(cred_dict, f)

def log_action(fname, user, action, ip):
    date = datetime.now().strftime("%d %b'%y")
    with open('log.csv', 'ab') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([fname, user, action, ip, date])

def send_long_msg(sock, msg):
    sz = len(msg)
    num_chunks = (sz+CHUNK_SIZE-1)/CHUNK_SIZE
    print "sending long", num_chunks
    assert num_chunks <= MAX_CHUNKS, msg[:50]
    sock.send( str(num_chunks).zfill(4) )
    for i in range(num_chunks):
        sock.send(msg[i*CHUNK_SIZE:(i+1)*CHUNK_SIZE])
    sock.recv(1)
    
def recv_long_msg(sock):
    num_chunks = int(sock.recv(4))
    print "receiving long", num_chunks
    msg = ""
    for i in range(num_chunks):
        msg += sock.recv(CHUNK_SIZE)
    sock.send(".")
    return msg


def server_signup(ctrl_sock, data_sock, comm_args, cred_lock):
    usr, pswd = comm_args[0], comm_args[1]
    cred_lock.acquire()
    cred_dict = read_cred()
    if usr in cred_dict:
        ctrl_sock.send("ERR: user already exists")
        cred_lock.release()
        return False
    else:
        cred_dict[usr] = pswd
        write_cred(cred_dict)
        cred_lock.release()
        os.mkdir(usr)
        os.chdir(usr)
        f = open("log.csv","w")
        f.close()
        ctrl_sock.send("ACK")
        return True

def client_signup(ctrl_sock, data_sock, username, password):
    hash_pswd = md5.new(password).hexdigest()
    ctrl_sock.send("signup#%s#%s" % (username, hash_pswd))

    resp = ctrl_sock.recv(1024)
    if resp == "ACK":
        print "signup successful"
        return True
    else:
        print resp
        return False


def server_signin(ctrl_sock, data_sock, comm_args):
    usr, pswd = comm_args[0], comm_args[1]
    cred_dict = read_cred()
    if usr not in cred_dict or cred_dict[usr] != pswd:
        ctrl_sock.send("ERR: invalid username or password")
        return False
    else:
        ctrl_sock.send("ACK")
        os.chdir(usr)
        return True
        
def client_signin(ctrl_sock, data_sock, username, password):
    hash_pswd = md5.new(password).hexdigest()
    ctrl_sock.send("signin#%s#%s" % (username, hash_pswd))
    
    resp = ctrl_sock.recv(1024)
    if resp == "ACK":
        print "signin successful"
        return True
    else:
        print resp
        return False


def server_signout(ctrl_sock, data_sock):
    os.chdir("..") # switch back to server root
    ctrl_sock.send("ACK")

def client_signout(ctrl_sock, data_sock):
    ctrl_sock.send("signout")
    resp = ctrl_sock.recv(1024)
    if resp == "ACK":
        print "signed out"
        return True
    else:
        print "unable to sign out"
        return False


def find_owner(f):
    path, fname = os.path.split(os.path.abspath(f))
    owner = os.path.split(path)[1]
    return owner

def server_list(ctrl_sock, data_sock):
    lines = ["{0: <30}{1: <20}{2: <8}".format("File", "User", "Modified"), "="*58]
    for f in os.listdir('.'):
        if f=="log.csv": continue
        ts = os.path.getmtime(f)
        date_str = datetime.utcfromtimestamp(ts).strftime('%b%d,%y')
        owner = find_owner(f)
        #lines.append(f + " " + owner + " " + date_str)
        lines.append("{0: <30}{1: <20}{2: <8}".format(f, owner, date_str))
    final_data = "\n".join(lines)
    send_long_msg(data_sock, final_data)
    ctrl_sock.send('ACK')

def client_list(ctrl_sock, data_sock):
    ctrl_sock.send('list')
    filelist = recv_long_msg(data_sock)
    ctrl_sock.recv(1024)
    print filelist


def server_delete(ctrl_sock, data_sock, comm_args, user, ip):
    fname = comm_args[0]
    if fname!="log.csv" and os.path.isfile(fname):
        os.remove(fname)
        log_action(fname, user ,'delete', ip)
        ctrl_sock.send("ACK")
    else:
        ctrl_sock.send("ERR: No such file")

def client_delete(ctrl_sock, data_sock):
    fname = raw_input("File to delete:")
    ctrl_sock.send('delete#%s' % fname)
    resp = ctrl_sock.recv(1024)
    if resp == "ACK":
        print "file deleted"
    else:
        print resp

        
def server_download(ctrl_sock, data_sock, comm_args, user, ip):
    fname = comm_args[0]
    if fname!="log.csv" and os.path.isfile(fname):
        with open(fname, "r") as f:
            contents = f.read()
        ctrl_sock.send("1")
        send_long_msg(data_sock, contents)
        log_action(fname, user, 'download', ip)
        ctrl_sock.send("ACK")
    else:
        ctrl_sock.send("0")
        ctrl_sock.send("ERR: No such file")
    
def client_download(ctrl_sock, data_sock):
    fname = raw_input("File to download:")
    if "/" in fname:
        print "invalid file"
        return
    ctrl_sock.send('download#%s'%fname)
    file_found = ctrl_sock.recv(1)
    if file_found == "1":
        contents = recv_long_msg(data_sock)
        with open(fname, "w") as f:
            f.write(contents)
    else:
        print "no data recd"
    resp = ctrl_sock.recv(1024)
    if resp == "ACK":
        print "download done"
    else:
        print resp

def server_upload(ctrl_sock, data_sock, comm_args, user, ip):
    fname = comm_args[0]
    if fname == "log.csv":
        ctrl_sock.send("1")
        ctrl_sock.send("ERR: Invalid file")
        return
    if os.path.isfile(fname):
        ctrl_sock.send("1")
        ctrl_sock.send("ERR: File already exists")
    else:
        ctrl_sock.send("0")
        contents = recv_long_msg(data_sock)
        with open(fname, "w") as f:
            f.write(contents)
        log_action(fname, user, 'upload', ip)
        ctrl_sock.send("ACK")
    
def client_upload(ctrl_sock, data_sock):
    pathtofile = raw_input("File to upload:")
    fpath, fname = os.path.split(pathtofile)
    if not os.path.isfile(pathtofile):
        print "file not found"
        return
    ctrl_sock.send('upload#%s'%fname)
    file_found = ctrl_sock.recv(1)
    if file_found != "1":
        with open(pathtofile, "r") as f:
            contents = f.read()
        send_long_msg(data_sock, contents)
    resp = ctrl_sock.recv(1024)
    if resp == "ACK":
        print "download done"
    else:
        print resp



















    
