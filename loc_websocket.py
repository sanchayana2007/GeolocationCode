# -*- coding: utf-8 -*-
import string
import random
import time
import datetime
import uuid
import json
from twisted.python import log
from twisted.internet import defer, reactor
import cyclone.websocket
from collections import defaultdict
from web_utils import *
from common import *
from vehicles import GetKdbData
# Redis modules.
import cyclone.redis
from jwt_auth import *
import s2sphere
from s2sphere import LatLng

'''
Concepts borrowed from
https://github.com/fiorix/txredisapi/blob/master/examples/cyclone_demo.py
'''

user_sockets = {}
def user_send_msg(uid, msg):
    try:
        ws = user_sockets[uid]
        log.msg("Sending notifcation to the user %s" % uid)
        #msg = json.loads(str(msg))
        ws.sendMessage(msg)
        resp = True
    except Exception:
        log.msg("WS for user %s does not exists!" % uid)
        resp = False
    return resp

def close_existing_socket(uid):
    ws = user_sockets[uid]
    ws.multiple_socket = True
    log.msg("On existing user close socket %s" % uid)
    del user_sockets[uid]
    ws.psconn.quit()
    ws.transport.loseConnection()

class RedisMixin(object):
    dbconn = None
    qf = None
    #psconn = None
    #channels = collections.defaultdict(lambda: [])
    ws = None

    @classmethod
    @defer.inlineCallbacks
    def setup(self, host, port, dbid, poolsize):
        # PubSub client connection
        RedisMixin.qf = cyclone.redis.SubscriberFactory()
        RedisMixin.qf.maxDelay = 20
        RedisMixin.qf.protocol = QueueProtocol

        # Normal client connection
        RedisMixin.dbconn = yield cyclone.redis.ConnectionPool(host, port,
                            dbid, poolsize)
        #RedisMixin.dbconn = cyclone.redis.Connection()

    #PubSub client connection
    def setup_ps(self, host, port):
        #ToDo: If there is more than one outstanding connection,
        #this will overwrite
        RedisMixin.ws = self
        log.msg("setup_ps success")
        reactor.connectTCP(host, port, RedisMixin.qf)

    def subscribe(self, channel):
        if self.psconn is None:
            raise cyclone.web.HTTPError(503)  # Service Unavailable

        self.psconn.subscribe(channel)
        log.msg("Client %s subscribed to %s" %
                (self.request.remote_ip, channel))

class QueueProtocol(cyclone.redis.SubscriberProtocol, RedisMixin, MongoMixin):
    users = MongoMixin.db.users

    def messageReceived(self, pattern, channel, message):
        # When new messages are published to Redis channels or patterns,
        # they are broadcasted to all HTTP clients subscribed to those
        # channels.
        log.msg("Got msg from redis on %s : %r" % (channel, message))
	#ToDo: Check if required
        if isinstance(message, unicode):
            log.msg("Channel message publish")
            self.ws.on_msg_published(message)
        #RedisMixin.broadcast(self, pattern, channel, message)

    #@defer.inlineCallbacks
    def connectionMade(self):
        self.psconn = self
        self.ws = RedisMixin.ws
	self.ws.psconn = self
	#ToDo: This has to go to Service Layer
	RedisMixin.ws = None
        msg = { 'msg_type' : 'conn_ready'}
        self.ws.sendMessage(str(msg))

	#ToDo: Handle Reconnect; all the above channels should be pushed to self.channels
	# and on reconnect just subscribe to self.channels.
        # If we lost connection with Redis during operation, we
        # re-subscribe to all channels once the connection is re-established.
        '''
        for channel in self.channels:
            if "*" in channel:
                self.psubscribe(channel)
            else:
                self.subscribe(channel)
        '''
    def connectionLost(self, why):
        print("connection Lost")

class LocationSocketHandler(cyclone.websocket.WebSocketHandler, RedisMixin, MongoMixin):
    users = MongoMixin.db.users
    entity = MongoMixin.db.entities
    trips = MongoMixin.db.trips
    routes = MongoMixin.db.routes
    vendors = MongoMixin.db.vendors

    def initialize(self, stats):
	self.is_notification = False
	self.is_live = False
	self.is_distance = False
	self.is_heartbeat = False
	self.multiple_socket = False
        self.single_socket = False
        self.stats = stats

    def connectionMade(self):
        log.msg("WS conn created")
        user = self.get_secure_cookie("user")
        #ToDo: token +  ws
	if (user == None):
            log.msg("user not found so treated as android user")
        else:
            user = user.strip('"')
            self.loc_user = str(user)
            self.setup_ps("127.0.0.1", 6379)
            log.msg("WS conn got from %s" % user)

    def connectionLost(self, reason):
        log.msg("WS lost conn with %s" % self.uid)
        #ToDo: Need to unsubscribe
        if self.multiple_socket is True:
            log.msg("Already removed the uid from dict")
            return
        try:
	    del user_sockets[self.uid]
        except:
            log.msg('WS close from non-users')
	self.psconn.quit()

    def messageReceived(self, data):
        log.msg("WS got msg : %r" % data)
        data = json.loads(data)
        msg_type = data['msg_type']

        if(msg_type == "register"):
            ret = dec_token(data['auth_token'])
            if ret == False:
                log.msg("WS scoket token validation failed!")
                self.transport.loseConnection()
                return
            self.uid = str(ret)
            #Only users need to go to the user_sockets array.
            #ToDo: Get the user role either from jwt token or from DB
            if 'source' in data and data['source'] == 'admin_portal':
                log.msg('WS Register for Admin Portal')
                self.setup_ps("127.0.0.1", 6379)
                return
            if self.uid in user_sockets:
                log.msg("WARN! socket already present so closing the previous one")
                #Keeping the new socket closing the existing socket.
                close_existing_socket(self.uid)
            if(self.uid):
                self.setup_ps("127.0.0.1", 6379)
		user_sockets[self.uid] = self
                log.msg("Socket Created added uid in global")
                self.single_socket = True
	        #self.is_heartbeat = True
            else:
                log.msg("WS scoket creation failed!")
                self.transport.loseConnection()
	    return

	#For any other message, the ws should be registeded
	if(self.uid == None):
            log.msg("self.uid == None, so returing")
            self.transport.loseConnection()
            #ToDo: Close Conn
	    return

        if(msg_type == "sub"):
            self.is_live = True
            topic = str('loc:' + data['vid'])
            self.psconn.subscribe(topic)
            return

        if(msg_type == "unsub"):
            topic = str('loc:' + data['vid'])
            self.psconn.unsubscribe(topic)
            return

        else:
            log.msg("WS conn got unknown msg from %r" % self.uid)


    #@defer.inlineCallbacks
    def on_msg_published(self, message):
        msg = json.loads(str(message))
        '''
        v_id = msg["v_id"]
        if(self.vid != v_id):
	    log.msg("Got data that i did not subscribe, or subscribed earlier")
	    #ToDo: unsubscribe v_id
	    return
        '''
	if(self.is_heartbeat):
            log.msg("Heartbeat notification returing")
            return
	if(self.is_live):
            log.msg("Publishing live location to ", self.uid)
            self.sendMessage(str(message))
	if(self.is_notification):
            loc = cyclone.escape.json_decode(message)
            log.msg("Sending the notification:%r" % self.uid)
            vlat = loc["latitude"]
            vlon = loc["longitude"]
            ulat = "12.8379176"
            ulon = "77.6391782"

            '''
            #Inside websocket not able to query on db so hardcoding the ulat and ulon
            rs = yield self.users.find({"_id": self.uid})
            if len(rs):
                ulat = rs["l_lattitude"]
                ulon = rs["l_longitude"]
                if(len(ulat)):
                    log.msg("Last lattitude available")
                else:
                    log.msg("Last lattitude not available taking default value")
                    ulat = "12.8379176"
                    ulon = "77.6391782"
            else:
                log.msg("uid is not available")
            '''
            log.msg("vlat:%r vlon:%r ulat:%r ulon:%r" % (vlat, vlon, ulat, ulon))
            distance = LatLng.from_degrees(float(vlat), float(vlon)).get_distance(LatLng.from_degrees(float(ulat), float(ulon))).radians
            distance = distance * 6371
            resp = {"resp_code": True,
                    "type": "distance",
                    "data": distance
                   }
            log.msg(resp)
            self.sendMessage(str(resp))
	    #ToDo: Do S2 Calculation


class StatsSocketHandler(cyclone.websocket.WebSocketHandler):
    def initialize(self, stats):
        self.stats = stats

        self._updater = task.LoopingCall(self._sendData)

    def connectionMade(self):
        self._updater.start(2)

    def connectionLost(self, reason):
        self._updater.stop()

    def _sendData(self):
        data = dict(visits=self.stats.todaysVisits(),
                    chatters=self.stats.chatters)
        self.sendMessage(cyclone.escape.json_encode(data))

class Stats(object):
    def __init__(self):
        self.visits = defaultdict(int)
        self.chatters = 0

    def todaysVisits(self):
        today = time.localtime()
        key = time.strftime('%Y%m%d', today)
        return self.visits[key]

    def newChatter(self):
        self.chatters += 1

    def lostChatter(self):
        self.chatters -= 1

    def newVisit(self):
        today = time.localtime()
        key = time.strftime('%Y%m%d', today)
        self.visits[key] += 1


@jwtauth
class VehcileSubscribeHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    entity = MongoMixin.db.entities
    users = MongoMixin.db.users
    vehicles = MongoMixin.db.vehicles
    get_data = GetKdbData()

    @defer.inlineCallbacks
    def post(self):
        if len(self.uid):
	    uid = str(self.uid)
	    ws = user_sockets[uid]
            '''
	    if len(ws.vid):
                log.msg("WS have existing vid so unsubscribing")
		ws.psconn.unsubscribe()
            else:
                log.msg("WS assiging a new vid")
            '''
	    ws.vid = self.request.arguments['vid']
            topic = str('loc:' + ws.vid)
            ws.psconn.subscribe(topic)
            msg_type = self.request.arguments['msg_type']
            log.msg("Subscribe user %s for vehicle %s, msg_type %s" % (self.uid, ws.vid, msg_type))
            if(msg_type == "distance"):
                status = True
	        ws.is_notification = True
                if ws.is_live == True:
                    ws.is_live = False
	        if ws.is_heartbeat == True:
                    self.is_heartbeat = False
                log.msg("Got msg type notification for distance updates")
                data = "distance updates"
            elif(msg_type == "live"):
                """
                Sending the vehicle last location
                because on map it will show the last location
                """
                dt = yield self.get_data.kdb_get_data(topic, from_tm, to_tm)
                if(dt == "NULL"):
                    loc_resp = []
                else:
                    loc_resp = dt
                if len(loc_resp):
                    #Android app will crash need to add resp_code in loc_mgr
                    msg = {"latitude": loc_resp[0]['latitude'], "longitude": loc_resp[0]['longitude'],
                            "time_stamp": loc_resp[0]['timestamp'], "v_id": ws.v_id}
                    status = True
                else:
                    #For temporary handling but it is not ri8 method, bcoz android app is crashing
                    msg = {"latitude": "0", "time_stamp": 0, "v_id": ws.vid, "longitude": "0"}
                    status = False
	        ws.is_live = True
	        if ws.is_notification == True:
	            ws.is_notification = False
	        if ws.is_heartbeat == True:
                    self.is_heartbeat = False
                data = "live updates"
                user_send_msg(self.uid, msg)
            elif(msg_type == "heartbeat"):
                """
                No notification
                """
                log.msg("Setting msg type is heartbeat")
	        self.is_heartbeat = True
                status = False
                ws.is_notification = False
                ws.is_live = False
                data = "heartbeat"
                status = True
            else:
                data = "unknown msg type"
                status = False
        else:
            data = "uid not available"
            status = False
        resp = {"resp_code" : True, "data": data, "status": status}
        self.write(resp)

