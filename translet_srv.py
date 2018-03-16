from flask import Flask, jsonify
from flask import json, request, Response
import MySQLdb
import logging
from app_globals import *
from db_handler import Query, get_userdata

logging.basicConfig(format="%(asctime)s %(funcName)s %(message)s",
                     filename=LOGDIR+"{0}.log".format(__name__),
                     level='DEBUG')
logger = logging.getLogger(__name__)
logger.info("Logger setup")
srvapp = Flask(__name__)


@srvapp.errorhandler(500)
def internal_error(e):
    msg = {
            'staus':500,
            'message':'Internal server error:{0}'.format(type(e))
    }
    resp = jsonify(msg)
    resp.status_code = 500
    return resp


@srvapp.route("/test/")
def index():
    logger.info("Test error message")
    return "Hello, world. You're at the polls index."

@srvapp.route("/auth/", methods = ['GET'])
def auth():
    #Validate uname/password or email/password
        #If not valid return 401 status with authorization failed
    try:
        if request.headers['Content-Type'] == 'text/plain':
            requestData = request.args
        elif request.headers['Content-Type'] == 'Application/json':
            requestData = json.loads(request.data)
        else:
            return Response('Invalid', status=401)
        user = ''
        if 'email' in requestData:
            logger.debug("email:"+requestData['email']+"Pwd:"+requestData['password'])
            user = "email='"+requestData['email']+"'"
        if 'uname' in requestData:
            logger.debug("uname:"+requestData['uname']+"Pwd:"+requestData['password'])
            user = "uname='"+requestData['uname']+"'"
        qry = "select uid from Users where "+user+" AND password='"+requestData['password']+"'"
        resp = ''
        qret = Query(qry).execute()
        if qret == None:
            msg = {
                    'status':404,
                    'message':__name__+':User/password mismatch.'
            }
            resp = jsonify(msg)
            resp.status_code = 404
        else:
            msg = {
                    'uid':qret[0][0]
            }
            resp = jsonify(msg)
            resp.status_code = 200
        return resp
    except Exception as e:
        logger.error('{0}:{1}'.format(type(e), str(e)))
        return internal_error()

@srvapp.route("/userdata/<uid>", methods = ['GET'])
def userdata(uid):
    resp = ''
    try:
        logger.debug('received user:{0}'.format(uid))
        udata = get_userdata(uid) 
        resp = jsonify(udata)
        resp.status_code = 200
        return resp
    except Exception as e:
        logger.error('{0}:{1}'.format(type(e), str(e)))
        return internal_error(e)

if __name__ == "main":
    srvapp.run(host='192.168.5.22')
