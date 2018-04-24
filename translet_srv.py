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
UID_UNAME = {}
UNAME_UID = {}

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
            'uid':str(-1),
            'uname':str(-1)
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
        qry = "select CAST(uid as CHAR),uname from Users where "+user+" AND password='"+data['password']+"'"
        qret = Query(qry).execute()
        if qret == None:
            msg = {
                    'status':1,
                    'message':__name__+':User/password mismatch.',
                    'uid':str(-1),
                    'uname':str(-1)
            }
        else:
            msg = {
                    'status':0,
                    'message':'authentication success',
                    'uid':qret[0][1]
            }
        UID_UNAME[qret[0][0]]=qret[0][1]
        UNAME_UID[qret[0][1]]=qret[0][0]
        return msg
    except Exception as e:
        logger.error('{0}:{1}'.format(type(e), str(e)))
        return internal_error(e)

def get_attendees(users):
    userlist = "','".join(users)
    q = "select CAST(uid as CHAR) from Users where email in ('"+userlist+"')"
    logger.debug(q)
    qret = Query(q).execute()
    uids = []
    pending = []
    if qret != None:
        logger.debug(repr(qret))
        #uids = [clients[str(r[0])] for r in qret]
        uids = [v[0] for v in filter(lambda e:e[0] in Clients, qret)]
        pending = [v[0] for v in filter(lambda e:e[0] not in Clients, qret)]
    return uids, pending
    
def add_session_to_DB(uid, sessionid):
    q = "insert into Confroom (sessionid, initiator) VALUES ('"+sessionid+"', "+UNAME_UID[uid]+")"
    logger.debug(q)
    qret = Query(q).execute()
    logger.debug(repr(qret))
    add_participant_entry(uid, sessionid)

def add_participant_entry(uid, sessionid):
    q = "insert into Participants (sessionid, uid) VALUES ('"+sessionid+"', "+UNAME_UID[uid]+")"
    logger.debug(q)
    qret = Query(q).execute()
    logger.debug(repr(qret))
    
def add_transcript_entry(uid, sessionid, message):
    q = "insert into Transcripts (uid, sessionid, text) VALUES ("+UNAME_UID[uid]+", '"+sessionid+"', '" + message + "')"
    logger.debug(q)
    qret = Query(q).execute()

def retrieve_session_history(sessionid):
    #q = "select CAST(uid as CHAR), text from Transcripts where sessionid='"+sessionid+"' order by timestamp"
    q = "select Users.uname,Transcripts.text from Users JOIN Transcripts on Users.uid = Transcripts.uid where Transcripts.sessionid='"+sessionid+"' order by timestamp"
    logger.debug(q)
    qret = Query(q).execute()
    msgs = []
    if qret == None:
        #return [{'uid':'None', 'message':'Empty'}]
        return []
    else:
        for r in qret:
            msg = {}
            msg['uid'] = r[0]
            msg['message'] = r[1]
            msgs.append(msg)
        logger.debug(msgs)
        return msgs

@srvapp.route(NAMESPACE+"/userdata/<uid>", methods = ['GET', 'POST'])
def userdata(uid):
    resp = None
    try:
        logger.debug('received user:{0}'.format(uid))
        udata = get_userdata(UNAME_UID[uid]) 
        logger.debug(repr(udata))
        resp = jsonify(udata)
        resp.status_code = 200
        return resp
    except Exception as e:
        logger.error('{0}:{1}'.format(type(e), str(e)))
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
        Clients[UNAME_UID[msg['uid']]] = request.sid
    else:
        emit('login', msg)
        return
    msg['usersession'] = request.sid
    emit('login', msg)
    time.sleep(2)
    logger.debug('Clients List:{0}'.format(' '.join(['{0}:{1}'.format(c, Clients[c]) for c in Clients])))
    logger.debug('Pending List:{0}'.format(' '.join(['({0} {1})'.format(e, Pending[e]) for e in Pending])))
    uid = msg['uid']
    if uid in Pending:
        emit('session_invite',
            {'status':0,
                'sessionid':Pending[uid]['sessionid'],
                'message':'user {0} invited you for LiveMeeting'.format(Pending[uid]['initiator'])})
        Pending.pop(uid, None)


@socketio.on('client_event', namespace=NAMESPACE)
def get_message(ev):
    session['rcount'] = session.get('rcount', 0) + 1
    emit('server_event',
         {'status':0, 'message': 'echo back2u-->'+ev['data'], 'count':session['rcount']})

@socketio.on('create_session', namespace=NAMESPACE)
def create_session(ev):
    sessionid = '{0}-{1}'.format(request.sid, ev['uid'])
    join_room(sessionid)
    attendees, pending = get_attendees(ev['invite'])
    add_session_to_DB(ev['uid'], sessionid)
    for attendee in attendees:
        emit('session_invite',
            {'status':0,
                'sessionid':sessionid,
                'message':'user {0} invited you for LiveMeeting'.format(ev['uid'])},
            room=Clients[attendee])    
    for e in pending:
        Pending[e] = {"sessionid":sessionid, "initiator":ev['uid']}

    logger.debug('Pending List:{0}'.format(' '.join(['({0} {1})'.format(e, Pending[e]) for e in Pending])))
    emit('create_session',
         {'status':0,
          'message': 'invites sent to [{0}]'.format(','.join([str(e) for e in attendees])),
          'sessionid':sessionid})

@socketio.on('get_history', namespace=NAMESPACE)
def get_History(ev):
    msg = 'User requested history for session {0}'.format(ev['sessionid'])
    msgs = retrieve_session_history(ev['sessionid'])
    emit('get_history',
         {'status':0, 'history':msgs})

@socketio.on('join_session', namespace=NAMESPACE)
def join_Session(ev):
    join_room(ev['sessionid'])
    add_participant_entry(ev['uid'], ev['sessionid'])
    msg = 'User {0} joined session.'.format(ev['uid'])
    msgs = retrieve_session_history(ev['sessionid'])
    emit('user_joined',
         {'status':0, 'uid':ev['uid'], 'history':msgs})
    emit('server_event',
         {'status':0, 'uid':ev['uid'], 'message':msg}, room=ev['sessionid'])

@socketio.on('leave_session', namespace=NAMESPACE)
def leave_Session(ev):
    logger.debug(ev)
    leave_room(ev['sessionid'])
    emit('user_left',
         {'status':0, 'message':'User {0} left session.'.format(ev['uid'])}, room=ev['sessionid'])

@socketio.on('close_session', namespace=NAMESPACE)
def close_Session(ev):
    if ev['uid'] == ev['sessionid'].split('-')[-1]:
        emit('session_closed',
             {'status':0, 'message':'session {0} is closing.'.format(ev['sessionid'])}, room=ev['sessionid'])
        time.sleep(2)
        close_room(ev['sessionid'])
    else:
        emit('server_event', {'message':'Not owner of the session. Can not close the session.'})

@socketio.on('session_event', namespace=NAMESPACE)
def broadcast_message(ev):
    add_transcript_entry(ev['uid'], ev['sessionid'], ev['message'])
    emit('server_broadcast',
         {'status':0, 'uid': ev['uid'], 'message':ev['message']}, room=ev['sessionid'])

if __name__ == "__main__":
    print('Starting server...')
    #socketio.run(srvapp, host='192.168.5.22')
    socketio.run(srvapp, host='ec2-52-43-208-107.us-west-2.compute.amazonaws.com')
