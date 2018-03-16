from flask import Flask, jsonify
from flask import json, request, Response
import MySQLdb
import logging
from app_globals import *
from server_process import *
from db_handler import Query, get_userdata

logging.basicConfig(format="%(asctime)s %(funcName)s:%(lineno)d %(message)s",
                     filename=LOGDIR+"{0}.log".format(__name__),
                     level='DEBUG')
mainlogger = logging.getLogger(__name__)
mainlogger.info("Logger setup")
srvapp = Flask(__name__)

@srvapp.errorhandler(400)
def invalid_request(e=None):
    msg = {
            'staus':400,
            'message':'Invalid request. header/parameters mismatch'
    }
    resp = jsonify(msg)
    resp.status_code = 400
    return resp

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
    mainlogger.info("Test error message")
    return "Hello, world. You're at the polls index."

@srvapp.route("/auth/", methods = ['GET', 'POST'])
def auth():
    #Validate uname/password or email/password
        #If not valid return 401 status with authorization failed
    try:
        if request.headers['Content-Type'] == 'text/plain':
            requestData = request.args
        elif request.headers['Content-Type'] == 'Application/json':
            requestData = json.loads(request.data)
        else:
            return invalid_request()
        user = ''
        if 'email' in requestData:
            mainlogger.debug("email:"+requestData['email']+"Pwd:"+requestData['password'])
            user = "email='"+requestData['email']+"'"
        if 'uname' in requestData:
            mainlogger.debug("uname:"+requestData['uname']+"Pwd:"+requestData['password'])
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
        mainlogger.error('{0}:{1}'.format(type(e), str(e)))
        return internal_error()

@srvapp.route("/userdata/<uid>", methods = ['GET'])
def userdata(uid):
    resp = None
    try:
        mainlogger.debug('received user:{0}'.format(uid))
        udata = get_userdata(uid) 
        mainlogger.debug(repr(udata))
        resp = jsonify(udata)
        resp.status_code = 200
        return resp
    except Exception as e:
        mainlogger.error('{0}:{1}'.format(type(e), str(e)))
        return internal_error(e)

@srvapp.route("/conference/", methods = ['POST'])
def new_conference():
    resp = None
    try:
        if request.headers['Content-Type'] != 'Application/json':
            return invalid_request()
        payload = json.loads(request.data)
        (resp_data, ret) = setup_conference(payload)
        if ret == E_EXISTS:
            msg = {
                    'status':409,
                    'message':'Active session currently exists',
                    'sessionid':resp_data['sessionid']
            }
            resp = jsonify(msg)
            resp.status_code = 409
            return resp
        resp = jsonify(resp_data)
        resp.status_code = 200
        return resp
    except Exception as e:
        mainlogger.error('{0}:{1}'.format(type(e), str(e)))
        return internal_error(e)

if __name__ == "main":
    srvapp.run(host='192.168.5.22')
