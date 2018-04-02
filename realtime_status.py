import cyclone.web
from twisted.python import log
from web_utils import *
from common import *
from loc_websocket import RedisMixin
import time

class RealTimeVehicleStatusHandler(MongoMixin, JsonHandler, RedisMixin):
    SUPPORTED_METHODS = ['GET', 'POST', 'DELETE', 'PUT']
    vehicles = MongoMixin.db.vehicles

    @defer.inlineCallbacks
    def get(self):
        res = yield self.vehicles.find()
        total_vehicle = len(res)
        active = 0
        inactive = 0
        not_connected = 0
        if total_vehicle:
            for r in res:
                v_id = str(r['_id'])
                topic = "loc:"+v_id
                loc_resp = yield RedisMixin.dbconn.lrange(topic, 0, 0)
                if len(loc_resp):
                    loc = cyclone.escape.json_decode(loc_resp[0])
                    timestamp = loc['time']
                    curr_time = int(time.time())
                    interval = curr_time - time_stamp
                    day = 86400                     #in secs
                    if(interval <= day):
                        if(interval <= 3600):
                            active = active + 1
                        else:
                            inactive = inactive + 1
                    else:
                        not_connected = not_connected + 1
                else:
                    not_connected = not_connected + 1
            v = {"total_vehicle": 1000, "active": 600, "inactive":300,
                 "not_connected": 100}
            resp = {"resp_code": True, "data": v}
        else:
            resp = {"resp_code": False, "data": "data not available"}
        self.write(resp)


class RealTimeUserStatusHandler(MongoMixin, JsonHandler):
    SUPPORTED_METHODS = ['GET', 'POST', 'DELETE', 'PUT']
    users = MongoMixin.db.users

    @defer.inlineCallbacks
    def get(self):
        res = yield self.users.find()
        total_user = len(res)
        active = 0
        inactive = 0
        not_used = 0
        if total_user:
            for r in res:
                #timestamp = r['time']
                timestamp = 8889999888
                curr_time = int(time.time())
                interval = curr_time - timestamp
                day = 86400                         #in secs
                if(interval <= day):
                    if(interval <= 3600):
                        active = active + 1
                    else:
                        inactive = inactive + 1
                else:
                    not_used = not_used + 1
            v = {"total_user": 1000, "active":500 , "inactive": 250, "not_used": 250}
            resp = {"resp_code": True, "data": v}
        else:
            resp = {"resp_code": False, "data": "data not available"}
        self.write(resp)

class RealTimeAlarmStatusHandler(MongoMixin, JsonHandler):
    SUPPORTED_METHODS = ['GET', 'POST', 'DELETE', 'PUT']
    alarms = MongoMixin.db.alarms
    users = MongoMixin.db.users
    vehicles = MongoMixin.db.vehicles
    entity = MongoMixin.db.entities

    @defer.inlineCallbacks
    def get(self):
        res = yield self.alarms.find()
        if len(res):
            result = []
            for r in res:
                rsp = yield self.users.find({"_id": r['u_id']})
                if len(rsp):
                    user_name = rsp[0]['full_name']
                else:
                    user_name = "NA"
                rsp = yield self.vehicles.find({"_id": r['v_id']})
                if len(rsp):
                    vehicle_name = rsp[0]['reg_num']
                else:
                    vehicle_name = "NA"
                rsp = yield self.entity.find({"_id": r['ent_id']})
                if len(rsp):
                    entity_name = rsp[0]['entity_name']
                else:
                    entity_name = "NA"
                v = {"user_name": user_name, "vehicle_name": vehicle_name, "entity_name": entity_name,
                     "alarm_type": r['alarm_type']}
                result.append(v)
            resp = {"resp_code": True, "data": result}
        else:
            resp = {"resp_code": False, "data": "data not available"}
        self.write(resp)
