import MySQLdb
import logging
from app_globals import *

logging.basicConfig(format="%(asctime)s %(funcName)s:%(lineno)d %(message)s",
                     filename=LOGDIR+"{0}.log".format(__name__),
                     level='DEBUG')
dblogger = logging.getLogger(__name__)
dblogger.info("Logger setup")

db = MySQLdb.connect(host='192.168.5.22',
                        user='commserver',
                        passwd='commserver',
                        db='CollabCommDB')

def get_userdata(uid):
    d = {}
    Q = "select sessionid, isActive from Confroom where initiator={0}".format(uid)
    result = Query(Q).execute()
    if result != None:
        d = dict([(r[0],r[1]) for r in result])
    return d;

class Query:
    def __init__(self, qstr):
        self.rawquery = qstr
    def execute(self):
        cur = db.cursor()
        qret = cur.execute(self.rawquery)
        if qret == 0:
            result = None
        else:
            result = cur.fetchall()
        return result
