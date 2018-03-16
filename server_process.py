from db_handler import *
from app_globals import *
import logging, traceback

logging.basicConfig(format="%(asctime)s %(funcName)s:%(lineno)d %(message)s",
                     filename=LOGDIR+"{0}.log".format(__name__),
                     level='DEBUG')

locallogger = logging.getLogger(__name__)
locallogger.info("Logger setup")

def setup_conference(req):
    q_find_session = 'select sessionid from Confroom where initiator = {0} and isActive = 1'
    q_create_session = """INSERT INTO Confroom (starttime, initiator, IsActive) VALUES ('{0}',{1},1)"""
    ecode = E_SUCCESS
    try:
        qret = Query(q_find_session.format(req['uid'])).execute()
        
        if qret == None:
            qret = Query(q_create_session.format(
                                                req['StartTime'],
                                                req['uid'])
                        ).execute()
            db.commit()
            qret = Query(q_find_session.format(req['uid'])).execute()
        else:
            ecode = E_EXISTS
            locallogger.debug(repr(qret))
        sid = qret[0][0]
        return ({'sessionid':qret[0][0]}, ecode)
    except Exception as e:
        locallogger.error(traceback.format_exc())
        locallogger.error('{0}:{1}'.format(type(e), str(e)))
        raise e
    
