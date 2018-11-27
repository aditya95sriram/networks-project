import os
import pickle
from hashlib import md5
import csv
from datetime import datetime
from getpass import getpass
try:
    from tqdm import tqdm
except ImportError:
    class tqdm():
        def __init__(self, **kwargs):
            pass
        def update(self, n):
            pass
        def close(self):
            pass

COMM_WIDTH = 100
def embed_msg(msg, width=COMM_WIDTH):
    return msg + " "*(width-len(msg))

def read_cred():
    with open("credentials.db", "rb") as f:
        cred_dict = pickle.load(f)
    return cred_dict


def write_cred(cred_dict):
    with open("credentials.db", "wb") as f:
        pickle.dump(cred_dict, f)


def log_action(fname, user, action, ip, cur_user=""):
    if cur_user == "": 
        logfile = "log.csv"
    else:
        print "logging extra to", cur_user
        logfile = "../%s/log.csv"%cur_user
    date = datetime.now().strftime("%d %b'%y")
    with open(logfile, 'ab') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([fname, user, action, ip, date])


def send_long_msg(sock, msg, progress=False):
    sz = len(msg)
    sz_msg = str(sz)
    sz_len = len(sz_msg)
    sz_char = chr(sz_len + ord('a') - 1)
    sock.send(sz_char)
    send_fix_msg(sock, sz_msg, sz_len)
    send_fix_msg(sock, msg, sz, progress)


def recv_long_msg(sock, progress=False):
    sz_char = sock.recv(1)
    sz_len = ord(sz_char) - ord('a') + 1
    sz_msg = recv_fix_msg(sock, sz_len)
    msg = recv_fix_msg(sock, int(sz_msg), progress)
    return msg


def send_fix_msg(sock, msg, msglen, progress=False):
    totalsent = 0
    if progress: pbar = tqdm(total=msglen, unit="kB", unit_scale=True)
    while totalsent < msglen:
        sent = sock.send(msg[totalsent:])
        if sent == 0:
            raise RuntimeError("socket connection broken")
        if progress: pbar.update(sent)
        totalsent = totalsent + sent
    if progress: pbar.close()


def recv_fix_msg(sock, msglen, progress=False):
    chunks = []
    bytes_recd = 0
    if progress: pbar = tqdm(total=msglen, unit="B", unit_scale=True)
    while bytes_recd < msglen:
        chunk = sock.recv(min(msglen - bytes_recd, 2048))
        if chunk == '':
            raise RuntimeError("socket connection broken")
        chunks.append(chunk)
        if progress: pbar.update(len(chunk))
        bytes_recd = bytes_recd + len(chunk)
    if progress: pbar.close()
    return ''.join(chunks)


def find_owner(f):
    while os.path.islink(f):
        f = os.readlink(f)
    path, fname = os.path.split(os.path.abspath(f))
    owner = os.path.split(path)[1]
    return owner


class Server(object):
    
    def __init__(self, ctrl_sock, data_sock, ip, cred_lock):
        self.ctrl_sock = ctrl_sock
        self.data_sock = data_sock
        self.user = ""
        self.ip = ip
        self.cred_lock = cred_lock
        
    def signup(self, args):
        usr, pswd = args[0], args[1]
        self.cred_lock.acquire()
        cred_dict = read_cred()
        if usr in cred_dict:
            self.ctrl_sock.send("ERR: user already exists")
            self.cred_lock.release()
            return False
        else:
            cred_dict[usr] = pswd
            write_cred(cred_dict)
            self.cred_lock.release()
            os.mkdir(usr)
            os.chdir(usr)
            f = open("log.csv","w")
            f.close()
            self.ctrl_sock.send("ACK")
            self.user = usr # user signed in
            return True
            
    def signin(self, args):
        usr, pswd = args[0], args[1]
        cred_dict = read_cred()
        if usr not in cred_dict or cred_dict[usr] != pswd:
            self.ctrl_sock.send("ERR: invalid username or password")
            return False
        else:
            self.ctrl_sock.send("ACK")
            os.chdir(usr)
            self.user = usr # user signed in
            return True

    def signout(self):
        os.chdir("..") # switch back to server root
        self.ctrl_sock.send("ACK")
        self.user = ""

    def list(self):
        fmt_str = "{0: <30}{1: <20}{2: <10}"
        lines = [fmt_str.format("File", "User", "Modified"), "=" * 60]
        for f in os.listdir('.'):
            if f == "log.csv": continue
            if not os.path.isfile(f):
                lines.append(fmt_str.format(f + "(deleted)", find_owner(f), "-"))
                continue
            ts = os.path.getmtime(f)
            date_str = datetime.utcfromtimestamp(ts).strftime('%b%d,%y')
            owner = find_owner(f)
            # lines.append(f + " " + owner + " " + date_str)
            lines.append(fmt_str.format(f, owner, date_str))
        final_data = "\n".join(lines)
        send_long_msg(self.data_sock, final_data)
        self.ctrl_sock.send('ACK')

    def delete(self, args):
        fname = args[0]
        if fname!="log.csv" and os.path.isfile(fname):
            os.remove(fname)
            log_action(fname, self.user ,'delete', self.ip)
            self.ctrl_sock.send("ACK")
        else:
            self.ctrl_sock.send("ERR: No such file")

    def download(self, args):
        fname = args[0]
        if fname!="log.csv" and os.path.isfile(fname):
            with open(fname, "r") as f:
                contents = f.read()
            self.ctrl_sock.send("1")
            send_long_msg(self.data_sock, contents)
            log_action(fname, self.user, 'download', self.ip)
            if os.path.islink(fname):
                log_action(fname, self.user, 'download', self.ip, find_owner(fname))
            self.ctrl_sock.send("ACK")
        else:
            self.ctrl_sock.send("0")
            self.ctrl_sock.send("ERR: No such file")

    def upload(self, args):
        fname = args[0]
        if fname == "log.csv":
            self.ctrl_sock.send("1")
            self.ctrl_sock.send("ERR: Invalid file")
            return
        if os.path.isfile(fname):
            self.ctrl_sock.send("1")
            self.ctrl_sock.send("ERR: File already exists")
        else:
            self.ctrl_sock.send("0")
            contents = recv_long_msg(self.data_sock)
            with open(fname, "w") as f:
                f.write(contents)
            log_action(fname, self.user, 'upload', self.ip)
            self.ctrl_sock.send("ACK")
            
    def share(self, args):
        fname, target = args[0], args[1]
        if not os.path.isfile(fname):
            self.ctrl_sock.send("ERR: File not found")
            return
        if not os.path.isdir("../%s"%target):
            self.ctrl_sock.send("ERR: User not found")
            return
        try:
            os.symlink(os.path.abspath(fname), "../%s/%s"%(target, fname))
        except OSError as err:
            if err.errno == 17:
                self.ctrl_sock.send("ERR: File already shared or exists")
                return
            else: raise
        log_action(fname, self.user, 'share', self.ip)
        log_action(fname, self.user, 'share', self.ip, target)
        self.ctrl_sock.send("ACK")

    def showlog(self):
        fmt_str = "{0: <30}{1: <20}{2: <10}{3: <17}{4: <10}"
        lines = [fmt_str.format("File", "User", "Action", "IP", "Date"), "="*87]
        with open("log.csv") as f:
            reader = csv.reader(f)
            for row in reader:
                lines.append(fmt_str.format(*row))
        final_data = "\n".join(lines)
        send_long_msg(self.data_sock, final_data)
        self.ctrl_sock.send('ACK')


class Client(object):
    
    def __init__(self, ctrl_sock, data_sock):
        self.ctrl_sock = ctrl_sock
        self.data_sock = data_sock
        self.user = ""
    
    def signup(self):
        username = raw_input("Username: ")
        password = getpass()
        hash_pswd = md5(password).hexdigest()
        command = embed_msg("signup#%s#%s" % (username, hash_pswd))
        send_fix_msg(self.ctrl_sock, command, COMM_WIDTH)
        resp = self.ctrl_sock.recv(1024)
        if resp == "ACK":
            print "signup successful"
            self.user = username
        else:
            print resp

    def signin(self):
        username = raw_input("Username: ")
        password = getpass()
        hash_pswd = md5(password).hexdigest()
        command = embed_msg("signin#%s#%s" % (username, hash_pswd))
        send_fix_msg(self.ctrl_sock, command, COMM_WIDTH)
        resp = self.ctrl_sock.recv(1024)
        if resp == "ACK":
            print "signin successful"
            self.user = username
        else:
            print resp

    def signout(self):
        command = embed_msg("signout")
        send_fix_msg(self.ctrl_sock, command, COMM_WIDTH)
        resp = self.ctrl_sock.recv(1024)
        if resp == "ACK":
            print "signed out"
            self.user = ""
        else:
            print "unable to sign out"

    def list(self):
        command = embed_msg('list')
        send_fix_msg(self.ctrl_sock, command, COMM_WIDTH)
        filelist = recv_long_msg(self.data_sock)
        self.ctrl_sock.recv(1024)
        print filelist

    def delete(self):
        fname = raw_input("File to delete:")
        command = embed_msg('delete#%s' % fname)
        send_fix_msg(self.ctrl_sock, command, COMM_WIDTH)
        resp = self.ctrl_sock.recv(1024)
        if resp == "ACK":
            print "file deleted"
        else:
            print resp

    def download(self):
        fname = raw_input("File to download:")
        if "/" in fname:
            print "invalid file"
            return
        command = embed_msg('download#%s'%fname)
        send_fix_msg(self.ctrl_sock, command, COMM_WIDTH)
        file_found = self.ctrl_sock.recv(1)
        if file_found == "1":
            contents = recv_long_msg(self.data_sock, True)
            with open(fname, "w") as f:
                f.write(contents)
        resp = self.ctrl_sock.recv(1024)
        if resp == "ACK":
            print "download done"
        else:
            print resp

    def upload(self):
        pathtofile = raw_input("File to upload:")
        fpath, fname = os.path.split(pathtofile)
        if not os.path.isfile(pathtofile):
            print "file not found"
            return
        command = embed_msg('upload#%s'%fname)
        send_fix_msg(self.ctrl_sock, command, COMM_WIDTH)
        file_found = self.ctrl_sock.recv(1)
        if file_found != "1":
            with open(pathtofile, "r") as f:
                contents = f.read()
            send_long_msg(self.data_sock, contents, True)
        resp = self.ctrl_sock.recv(1024)
        if resp == "ACK":
            print "upload done"
        else:
            print resp

    def share(self):
        fname = raw_input("File to share:")
        target = raw_input("User to share with:")
        if fname == "log.csv":
            print "file not found"
            return
        command = embed_msg("share#%s#%s" %(fname, target))
        send_fix_msg(self.ctrl_sock, command, COMM_WIDTH)
        resp = self.ctrl_sock.recv(1024)
        if resp == "ACK":
            print "shared successfully"
        else:
            print resp

    def showlog(self):
        command = embed_msg("showlog")
        send_fix_msg(self.ctrl_sock, command, COMM_WIDTH)
        logdata = recv_long_msg(self.data_sock)
        self.ctrl_sock.recv(1024)
        print logdata        

