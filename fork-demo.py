import os
from time import sleep

childpid = os.fork()
if childpid < 0:
   print "fork failed"
elif childpid == 0:
   sleep(5)
   print 'A new child ',  os.getpid()
else:
   print "waiting"
   os.wait()
   print "parent: %d, child: %d" % (os.getpid(), childpid)
print "outside", os.getpid()
