from flask import Flask
from flask import json, request, Response
import MySQLdb
import json
import logging

LOGDIR='/var/log/translet/'
logging.basicConfig(format="%(asctime)s %(funcName)s %(message)s",
                     filename=LOGDIR+"{0}.log".format(__name__),
                     level='DEBUG')
logger = logging.getLogger(__name__)
logger.info("Logger setup")
srvapp = Flask(__name__)

db = MySQLdb.connect(host='192.168.5.22',
                        user='commserver',
                        passwd='commserver',
                        db='CollabCommDB')

@srvapp.route("/test/")
def index():
    logger.info("Test error message")
    return "Hello, world. You're at the polls index."

@srvapp.route("/auth/", methods = ['POST', 'GET'])
def auth():
    #Validate uname/password or email/password
        #If not valid return 401 status with authorization failed
    try:
        if request.headers['Content-Type'] == 'text/plain':
            requestData = request.args
            logger.debug(repr(request))
        elif request.headers['Content-Type'] == 'Application/json':
            requestData = json.loads(request.data)
        else:
            return Response('Invalid', status=401)
        logger.debug("data:"+repr(requestData))
        status = 200
        cur = db.cursor()
        user = ''
        if 'email' in requestData:
            logger.debug("email:"+requestData['email']+"Pwd:"+requestData['password'])
            user = "email='"+requestData['email']+"'"
        if 'uname' in requestData:
            logger.debug("uname:"+requestData['uname']+"Pwd:"+requestData['password'])
            user = "uname='"+requestData['uname']+"'"
        qry = "select uid from Users where "+user+" AND password='"+requestData['password']+"'"
        logger.debug("Executing:"+qry)
        resp = ''
        qret = cur.execute(qry)
        if qret == 0:
            resp = __name__+':User/password mismatch.'
            status = 401
        else:
            resp = str(cur.fetchone()[0])
    except Exception as e:
        resp = __name__+':Server exception'
        logger.error('{0}:{1}'.format(type(e), str(e)))
        status = 401
    return Response(resp, status)

@srvapp.route("/userdata/<uid>", methods = ['GET'])
def get_userdata(uid):
    resp = ''
    status = 201
    try:
        resp = 'received user:{0}'.format(uid)
    except Exception as e:
        resp = __name__+':server exception'
        logger.error('{0}:{1}'.format(type(e), str(e)))
        status = 401
    return Response(resp, status)

if __name__ == "main":
    srvapp.run(host='192.168.5.22')
