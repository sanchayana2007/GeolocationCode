from __future__ import division
import cyclone.web
import cyclone.httpclient
from twisted.python import log
from twisted.internet import defer
from twisted.internet.defer import returnValue
from web_utils import *
from kariosdb import *
from common import *
from jwt_auth import jwtauth
import time
import s2sphere
from s2sphere import LatLng, CellId

class GetKdbData(KariosDBConnection):
    ssl = False
    conn = KariosDBConnection('127.0.0.1', '8080', False)

    @defer.inlineCallbacks
    def kdb_get_data(self, topic, from_tm, to_tm):
        loc = []
        result = []
        temp = 0
        j = k = 0
        max_speed = 0
        avg_speed = 0
        dist = 0
        if(from_tm != 0):
            r = yield self.conn.read_absolute(self, [topic], from_tm, to_tm)
            length = r['queries'][0]['sample_size']
            if length:
                res = r['queries'][0]['results'][0]['values']
                for rs in res:
                    val = CellId(rs[1])
                    lat = val.to_lat_lng().lat().degrees
                    longt = val.to_lat_lng().lng().degrees
                    tm = rs[0] / 1000
                    v = {"latitude": lat, "longitude": longt, "timestamp": tm, "speed": 0, 'distance': -1}
                    loc.append(v)
                es = r['queries'][0]['results'][0]['tags']['speed']
                if len(es):
                    for x in es:
                        x = float(x)
                        loc[j]['speed'] = x
                        j = j + 1
                        temp = temp + x
                    max_speed = max(es)
                    avg_speed = temp / len(es)
                    avg_speed = float(format(avg_speed, '.2f'))
                    result.append(avg_speed)
                    result.append(float(max_speed))
                try:
                    ds = r['queries'][0]['results'][0]['tags']['distance']
                    if len(ds):
                        for x in ds:
                            x = float(x)
                            dist = dist + x
                            k = k + 1
                            if(dist == 0.0):
                                continue
                            loc[k]['distance'] = dist
                except Exception, e:
                    log.msg("No distance recorded in DB for this vehicle")
                result.append(loc)
                data = result
            else:
                data = "NULL"
        else:
            r = yield self.conn.read_absolute(self, [topic], 0)
            n = r['queries'][0]['sample_size']
            if n:
                es = r['queries'][0]['results'][0]['values']
                val = CellId(es[n-1][1])
                lat = val.to_lat_lng().lat().degrees
                longt = val.to_lat_lng().lng().degrees
                tm = es[n-1][0] / 1000
                sp = r['queries'][0]['results'][0]['tags']['speed']
                x = len(sp)
                speed = sp[x-1]
                try:
                    sp = r['queries'][0]['results'][0]['tags']['distance']
                    x = len(sp)
                    dist = sp[x-1]
                except Exception, e:
                    log.msg("No distance recorded in DB for this vehicle")
                    dist = -1
                v = {"latitude": lat, "longitude": longt, "timestamp": tm, 'speed': speed, 'distance': dist}
                result.append(v)
                data = result
            else:
                data = "NULL"
        returnValue(data)

@jwtauth
class VehicleHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    vehicles = MongoMixin.db.vehicles
    users = MongoMixin.db.users
    devices = MongoMixin.db.devices
    entity = MongoMixin.db.entities

    @defer.inlineCallbacks
    def get(self):
        try:
            u_id = self.get_arguments('u_id')
            u_id = u_id[0]
            rs = yield self.users.find({"_id": ObjectId(self.u_id)})
        except Exception, e:
            rs = yield self.users.find({"_id": ObjectId(self.uid)})
        result = []
        if len(rs):
            vehicle_ids = rs[0]["vehicles"]
            log.msg("Data are in tables")
            if len(vehicle_ids):
                for v_id in vehicle_ids:
                    res = yield self.vehicles.find({"_id": v_id})
                    if len(res):
                        for r in res:
                            rsp = yield self.entity.find({"_id": r['entity_id']})
                            if len(rsp):
                                mob_num = rsp[0]['mobile_number']
                            else:
                                mob_num = "NA"
                            es = yield self.users.find({"role": "driver", "mobile_number": r["driver_number"]})
                            if len(es):
                                dr_name = es[0]['full_name']
                            else:
                                dr_name = "NA"
                            v = {"v_id": str(r["_id"]), "reg_num": r["reg_num"], "color": r["colour"],
                                 "model": r["model"], "make": r["make"], "device_id": str(r["dev_id"]),
                                 "driver_number": r["driver_number"], "entity_id": str(r['entity_id']),
                                 "admin_number": mob_num, "driver_name": dr_name}
                            result.append(v)
                resp = {'resp_code': True, 'vehicles_data': result}
            else:
                log.msg("No vehicles present")
                resp = {'resp_code': False, 'vehicles_data': "UNAV"}                 #UNAV: User not assign to Vehicle
        else:
            resp = {'resp_code': False, 'vehicles_data': "NULL"}
        self.write(resp)

    @defer.inlineCallbacks
    def post(self):
        u_id = self.get_arguments('u_id')
        u_id = u_id[0]
	reg_num = self.request.arguments['reg_num']
        maker = self.request.arguments['make']
        model = self.request.arguments['model']
        colour = self.request.arguments['colour']
        dev_id = "Not_assigned"
        driver_num = "Not_assigned"
        rs = yield self.vehicles.find({"reg_num": reg_num})
        if len(rs):
            resp = {'resp_code': False, 'data': 'reg_num is already registered'}
        else:
            yield self.vehicles.insert({"reg_num": reg_num, "make": maker, "model": model, "colour": colour,
                "dev_id": dev_id, "driver_number": driver_num, "entity_id": "Not_assigned"})
            v_id = rs[0]["_id"]
            yield self.users.find_and_modify(
                query = {"_id": ObjectId(u_id)},
                update = {"$push": {"vehicles": v_id}}
            )
            resp = {'resp_code': True, 'data': 'inserted successfully'}
        self.write(resp)

    @defer.inlineCallbacks
    def delete(self):
        v_id = self.get_arguments('v_id')
        v_id = v_id[0]
        res = yield self.vehicles.find({"_id": ObjectId(v_id)})
        if len(res):
            device_id = res[0]['dev_id']
        yield self.vehicles.remove({"_id": ObjectId(v_id)})
        rs = yield self.users.find({"vehicles": [ObjectId(v_id)]})
        if len(rs):
            for r in rs:
                u_id = r[0]["_id"]
                yield self.users.find_and_modify(
                    query = {"_id": ObjectId(u_id)},
                    update = {"$pull": {"vehicles": {"$in": [ObjectId(v_id)]}}}
                )
            if(device_id == "Not_assigned"):
                resp = {'resp_code': False, 'data': "delete failed"}
            else:
                yield self.devices.find_and_modify(
                    query = {"_id": device_id},
                    update = {"$set": {"status": "new"}}
                )
                resp = {'status_code': True, 'data': 'successfully deleted'}
        else:
            resp = {'status_code': False, 'data': 'delete failed'}
        self.write(resp)

    @defer.inlineCallbacks
    def put(self):
        v_id = self.get_arguments('v_id')
        v_id = v_id[0]
        resp = yield self.vehicles.find({"_id": ObjectId(v_id)})
        dev_id = resp[0]["dev_id"]
        reg_num = self.request.arguments['reg_num']
	maker = self.request.arguments['make']
        model = self.request.arguments['model']
        colour = self.request.arguments['colour']
        rs = yield self.vehicles.find_and_modify(
            query = {"vehicle_id": ObjectId(v_id)},
            update = {"$set": {"reg_num": reg_num, "make": maker, "model": model,
                    "colour": colour}}
        )
        self.write({'status_code': True, 'data': 'Updated Successfully'})

@jwtauth
class CurrentVehicleDetailsHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    vehicles = MongoMixin.db.vehicles
    entity = MongoMixin.db.entities
    users = MongoMixin.db.users
    devices = MongoMixin.db.devices

    @defer.inlineCallbacks
    def get(self):
        u_id = self.uid
        rs = yield self.users.find({"_id": ObjectId(u_id)})
        if len(rs):
            ent_id = rs[0]['entity_id']
            if(ent_id == 'Not_assigned'):
                resp = {"resp_code": True, "data": "No data available"}
            else:
                result = []
                rsp = yield self.entity.find({"_id": ent_id})
                if len(rsp):
                    ent_name = rsp[0]['entity_name']
                else:
                    ent_name = 'NA'
                if(ent_name == 'xlayer' or ent_name == 'etrance'):
                    es = yield self.vehicles.find()
                    if len(es):
                        for r in es:
                            rsp = yield self.entity.find({"_id": r['entity_id']})
                            if len(rsp):
                                entity_name = rsp[0]['entity_name']
                            else:
                                entity_name = 'NA'
                            er = yield self.devices.find({"_id": r['dev_id']})
                            if len(er):
                                dev_num = er[0]['mobile_number']
                            else:
                                dev_num = "None"
                            erp = yield self.users.find({"mobile_number": r["driver_number"]})
                            if len(erp):
                                dr_name = erp[0]['full_name']
                            else:
                                dr_name = "None"
                            v = {"v_id": str(r["_id"]), "reg_num": r["reg_num"], "color": r["colour"],
                                 "model": r["model"], "make": r["make"], "device_id": str(r["dev_id"]),
                                 "driver_name": dr_name, "entity_id": str(r['entity_id']),
                                 "entity_name": entity_name, "device_number": dev_num, "device_type": r["dev_type"]}
                            result.append(v)
                else:
                    es = yield self.vehicles.find({"entity_id": ent_id})
                    if len(es):
                        for r in es:
                            er = yield self.devices.find({"_id": r['dev_id']})
                            if len(er):
                                dev_num = er[0]['mobile_number']
                            else:
                                dev_num = "None"
                            erp = yield self.users.find({"mobile_number": r["driver_number"]})
                            if len(erp):
                                dr_name = erp[0]['full_name']
                            else:
                                dr_name = "None"
                            v = {"v_id": str(r["_id"]), "reg_num": r["reg_num"], "color": r["colour"],
                                 "model": r["model"], "make": r["make"], "device_id": str(r["dev_id"]),
                                 "driver_name": dr_name, "entity_id": str(r['entity_id']),
                                 "entity_name": ent_name, "device_number": dev_num, "device_type": r["dev_type"]}
                            result.append(v)
                resp = {'resp_code': True, 'vehicles': result}
        else:
            resp = {'resp_code': False, 'detail': 'No data available'}
        self.write(resp)


@jwtauth
class LocationHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    users = MongoMixin.db.users
    get_data = GetKdbData()

    @defer.inlineCallbacks
    def get(self):
        u_id = self.uid
        ulat = None
        v_id = self.get_arguments('v_id')
        v_id = v_id[0]
        eta = '--'
        try:
            #user location is optional
            ulat = str(self.get_arguments('lat')[0]);
            ulong = self.get_arguments('long')[0];
        except Exception:
            log.msg('location API invoked with out current coordinates')
        t = int(time.time())
        topic = 'loc:' + v_id
        data = yield self.get_data.kdb_get_data(topic, 0, 0)
        loc_resp = data[2]
        loc_arr = []
        if len(loc_resp):
            for r in loc_resp:
                v = {"latitude": float(r['latitude']), "longitude": float(r['longitude']), "timestamp": r['time_stamp']}
                loc_arr.append(v)
            if ulat == '0.0':
                eta = '--'
            else:
                vlat = str(loc_arr[0]['latitude'])
                vlong = str(loc_arr[0]['longitude'])
                url = 'https://maps.googleapis.com/maps/api/distancematrix/json?units=metric&'\
                      'origins='+vlat+','+vlong+'&destinations='+ulat+','+ulong+'&key=AIzaSyBWRjrLgBiZU7Zfive_eCR8DL0tMzEhkOw'
                gresp = yield cyclone.httpclient.fetch(url)
                print("Map response: %r" % gresp.body)
                g = cyclone.escape.json_decode(gresp.body)
                #eta = g['rows'][0]['elements'][0]['duration']['text']+' '+g['rows'][0]['elements'][0]['distance']['text']
                eta = g['rows'][0]['elements'][0]['duration']['text']
                eda = g['rows'][0]['elements'][0]['distance']['text']

                """
                Here we are updating users location for realtime status and notification
                """
                yield self.users.find_and_modify(
                    query = {"_id": u_id},
                    update = {"$set":
                                {"l_latatitude": ulat,
                                 "l_longitude": ulong,
                                 "l_update_time": t
                                }
                             })
            val = True
        else:
            val = False
        log.msg(loc_arr)
        resp = {"resp_code": val, "location_data": loc_arr, 'estimated_time': eta, "distance": eda} #NDA : Location data not avail
        self.write(resp)

class GetLocationByTimeHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    get_data = GetKdbData()

    @defer.inlineCallbacks
    def get(self):
        v_id = self.get_arguments('v_id')
        v_id = v_id[0]
        from_tm = self.get_arguments('start_time')
        from_tm = int(from_tm[0])
        to_tm = self.get_arguments('end_time')
        to_tm = int(to_tm[0])
        max_speed = 0
        avg_speed = 0
        topic = 'loc:' + v_id
        #location subscribe from kairosdb
        if(from_tm != 0 and to_tm != 0):
            if(from_tm < to_tm):
                dt = yield self.get_data.kdb_get_data(topic, from_tm, to_tm)
                if(dt == "NULL"):
                    val = False
                    data = "NULL"
                else:
                    val = True
                    avg_speed = dt[0]
                    max_speed = dt[1]
                    data = dt[2]
            else:
                val = False
                data = "ETIS"   #end_time can not be smaller than the start_time
        else:
            val = False
            data = "NSTG"   #no specific time given
        resp = {"resp_code": val, "location_data": data, "avg_speed": avg_speed, "max_speed": max_speed}
        self.write(resp)

class GetLocationByTripHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    vehicles = MongoMixin.db.vehicles
    get_data = GetKdbData()

    @defer.inlineCallbacks
    def get(self):
        v_id = self.get_arguments('v_id')
        v_id = v_id[0]
        max_speed = 0
        avg_speed = 0
        rs = yield self.vehicles.find({"_id": ObjectId(v_id)})
        if len(rs):
            from_tm = rs[0]['start_time']
            to_tm = int(time.time())
            topic = 'loc:'+v_id
            if(from_tm != 0):
                if(from_tm < to_tm):
                    dt = yield self.get_data.kdb_get_data(topic, from_tm, to_tm)
                    if(dt == "NULL"):
                        val = False
                        data = "NULL"
                    else:
                        avg_speed = dt[0]
                        max_speed = dt[1]
                        data = dt[2]
                        val = True
                else:
                    val = False
                    data = "ICT" #invalid current time
            else:
                dt = yield self.get_data.kdb_get_data(topic, from_tm, to_tm)
                if(dt == 'NULL'):
                    val = False
                    data ="NULL"  #vehicle is in stop mode
                else:
                    val = True
                    data = dt
        else:
            val = False
            data = "IVID"    #Invalid vehicle
        resp = {"resp_code": val, "data": data, "avg_speed": avg_speed, "max_speed": max_speed}
        self.write(resp)


