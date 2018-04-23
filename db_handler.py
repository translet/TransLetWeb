import MySQLdb
import logging
from app_globals import *
import traceback, thread, time

logging.basicConfig(format="%(asctime)s %(funcName)s:%(lineno)d %(message)s",
                     filename=LOGDIR+"{0}.log".format(__name__),
                     level='DEBUG')
dblogger = logging.getLogger(__name__)
dblogger.info("Logger setup")


def keep_alive():
    while True:
        time.sleep(28000)
        Query('SELECT 1').execute()
        dblogger.info('Keepalive sent')

class DB:
    conn = None
    def __init__(self):
        count=1
        self.conn = MySQLdb.connect(host='localhost',
                        user='commserver',
                        passwd='CommPass',
                        db='TransLetDB')
	#self.conn.autocommit = True
        thread.start_new_thread(keep_alive)

    def commit(self):
        dblogger.error('Committing conn')
        self.conn.commit()
    def cursor(self):
        try:
            cur = self.conn.cursor()
        except Exception as e:
            dblogger.error('Exception occured:{0}'.format(str(e)))
            self.conn = MySQLdb.connect(host='localhost',
                            user='commserver',
                            passwd='CommPass',
                            db='TransLetDB')
            cur = self.conn.cursor()
        return cur

db = DB()

def get_userdata(uid):
    udata = []
    Q = "select sessionid from Participants where uid={0} limit 10".format(uid)
    result = Query(Q).execute()
    if result != None:
        for r in result:
            d = {}
            d['sessionid'] = r[0]
            udata.append(d)
    return udata

class Query:
    def __init__(self, qstr):
        self.rawquery = qstr
    def execute(self):
        try:
            cur = db.cursor()
            qret = cur.execute(self.rawquery)
            if qret == 0:
                result = None
            else:
                result = cur.fetchall()
            db.commit()
            dblogger.error('Closing cursor')
            cur.close()
            return result
        except Exception as e:
            dblogger.error('Execute:{0}'.format(traceback.format_exc()))
