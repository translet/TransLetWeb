#For webServer
import eventlet
eventlet.monkey_patch()

from threading import Lock
#For Flask based webapplication
from flask import Flask, jsonify, json
from flask import session, request, Response, render_template

#For Flask-socketio
from flask_socketio import SocketIO, rooms, emit, disconnect
from flask_socketio import join_room, leave_room, close_room

#App businesslogic
import logging, time
from app_globals import *
from server_process import *
from db_handler import Query, get_userdata

async_mode = None
Clients = {}
Pending = {}
NAMESPACE = '/translet'

logger = logging.getLogger(__name__)
logger.info("Logger setup")
srvapp = Flask(__name__)
srvapp.config['SECRET_KEY'] = 'translet'

socketio = SocketIO(srvapp)
thread = None
thread_lock = Lock()

def internal_error(e):
    msg = {
            'status':500,
            'message':'Internal server error:{0}'.format(type(e)),
            'uid':str(-1)
    }
    return msg

def bg_thread():
    count = 0
    while True:
        socketio.sleep(3600)
        count += 1
        socketio.emit('server_msg',
                      {'data': 'Server generated event', 'count': count},
                      namespace = NAMESPACE)

@srvapp.route("/")
def index():
    return render_template('index.html', async_mode=socketio.async_mode)

'''
@srvapp.route("/testurl/")
def index():
    return "Hello, world. Server poll test passed"
'''

def auth(data):
    #Validate uname/password or email/password
    try:
        if 'email' in data:
            logger.debug("email:"+data['email']+"Pwd:"+data['password'])
            user = "email='"+data['email']+"'"
        if 'uname' in data:
            logger.debug("uname:"+data['uname']+"Pwd:"+data['password'])
            user = "uname='"+data['uname']+"'"
        qry = "select uid from Users where "+user+" AND password='"+data['password']+"'"
        qret = Query(qry).execute()
        if qret == None:
            msg = {
                    'status':1,
                    'message':__name__+':User/password mismatch.',
                    'uid':str(-1)
            }
        else:
            msg = {
                    'status':0,
                    'message':'authentication success',
                    'uid':str(qret[0][0])
            }
        return msg
    except Exception as e:
        logger.error('{0}:{1}'.format(type(e), str(e)))
        return internal_error(e)

def get_attendees(users):
    userlist = "','".join(users)
    q = "select uid from Users where email in ('"+userlist+"')"
    qret = Query(q).execute()
    uids = []
    if qret != None:
        #uids = [clients[str(r[0])] for r in qret]
        uids = filter(lambda e:str(e) in Clients, qret[0]);
        pending = filter(lambda e:str(e) not in Clients, qret[0]);
    return uids, pending
    
    
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

'''SocketIO eventHandlers'''
@socketio.on('connect', namespace=NAMESPACE)
def connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=bg_thread)
    logger.debug('Connection request from {0}'.format(request.sid))
    emit('connect', {'status':0, 'message':'Connected', 'sid':request.sid})

@socketio.on('disconnect_event', namespace=NAMESPACE)
def disconnect_event():
    emit('disconnect',
         {'status':0, 'message':'Disconnected!'})
    disconnect()

@socketio.on('disconnect', namespace=NAMESPACE)
def disconnect():
    logger.info('Client disconnected {0}'.format(str(request.sid)))

@socketio.on('login', namespace=NAMESPACE)
def login(ev):
    msg = auth(ev)
    if msg['status'] == 0:
        Clients[msg['uid']] = request.sid
    msg['usersession'] = request.sid
    emit('login', msg)
    time.sleep(3)
    uid = msg['uid']
    if (uid in Pending):
        emit('session_invite',
            {'status':0,
                'sessionid':Pending[uid],
                'message':'{0} user invited you for LiveMeeting'.format(Pending['initiator'])})


@socketio.on('client_event', namespace=NAMESPACE)
def get_message(ev):
    session['rcount'] = session.get('rcount', 0) + 1
    emit('server_event',
         {'status':0, 'message': 'echo back2u-->'+ev['data'], 'count':session['rcount']})

@socketio.on('create_session', namespace=NAMESPACE)
def create_session(ev):
    sessionid = request.sid+'-'+ev['uid']
    join_room(sessionid)
    attendees, pending = get_attendees(ev['invite'])
    for attendee in attendees:
        emit('session_invite',
            {'status':0,
                'sessionid':sessionid,
                'message':'{0} user invited you for LiveMeeting'.format(ev['uid'])},
            room=Clients[attendee])    
    for e in pending:
        Pending[e] = {"sessionid":sessionid, "initiator":ev['uid']}

@socketio.on('join_Session', namespace=NAMESPACE)
def join_Session(ev):
    join_room(ev['sessionid'])
    emit('user_joined',
         {'status':0, 'uid':ev['uid'], 'message':'User {0} joined session.'.format(ev['uid'])}, room=ev['sessionid'])

@socketio.on('leave_Session', namespace=NAMESPACE)
def leave_Session(ev):
    leave_room(ev['sessionid'])
    emit('user_left',
         {'status':0, 'message':'User {0} left session.'.format(ev['uid'])})

@socketio.on('close_Session', namespace=NAMESPACE)
def close_Session(ev):
    emit('session_closed',
         {'status':0, 'message':'session {0} is closing.'.format(ev['sessionid'])}, room=ev['sessionid'])
    close_room(ev['sessionid'])

@socketio.on('session_event', namespace=NAMESPACE)
def broadcast_message(ev):
    emit('server_broadcast',
         {'status':0, 'uid': ev['uid'], 'message':ev['message']}, room=ev['sessionid'])

if __name__ == "__main__":
    print('Starting server...')
    socketio.run(srvapp, host='192.168.5.22')
