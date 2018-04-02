import cyclone.web
from twisted.python import log
from web_utils import *
from common import *
from jwt_auth import jwtauth

@jwtauth
class DeviceHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    devices = MongoMixin.db.devices
    vehicles = MongoMixin.db.vehicles
    users = MongoMixin.db.users
    entity = MongoMixin.db.entities

    @defer.inlineCallbacks
    def get(self):
        v_id = self.get_arguments('v_id')
        v_id = v_id[0]
        res = yield self.vehicles.find({"_id": ObjectId(v_id)})
        if len(res):
            dev_id = res[0]["dev_id"]
            if(dev_id == "Not_assigned"):
                resp = {'resp_code': -1, 'data': "No data Available"}
            else:
                rs = yield self.devices.find({"_id": dev_id})
                if len(rs):
                    log.msg("Data are in tables")
                    for r in rs:
                        v = {"d_id": str(dev_id), "imei": r["imei"], "device_type": r["dev_type"],
                                "phone_number": r["mobile_number"], "status": r["status"], "entity_id": str(r['entity_id'])}
                    resp = {'resp_code': True, 'data': v}
                else:
                    resp = {'resp_code': False, 'data': "No data Available"}
        else:
            resp = {'resp_code': False, 'data': "No data Available"}

    @defer.inlineCallbacks
    def post(self):
	imei = self.request.arguments['imei']
        dev_type = self.request.arguments['dev_type']
        mob_num = self.request.arguments['mob_num']
        rs = yield self.devices.find({"imei": imei})
        if len(rs):
            rcode = False
            data = 'device already present'
        else:
            er = yield self.users.find({"_id": ObjectId(self.uid)})
            if len(er):
                entity_id = er[0]['entity_id']
                erp = yield self.entity.find({"_id": entity_id})
                if len(er):
                    ent_name = erp[0]['entity_name']
                    if(ent_name == 'xlayer' or ent_name == 'etrance'):
                        try:
                            ent_id = self.request.arguments['ent_id']
                        except Exception, e:
                            ent_id = None
                        if(ent_id != None):
                            if(str(ent_id) == 'none'):
                                rsp = yield self.entity.find({"entity_name": "xlayer"})
                                if len(rsp):
                                    ent_id = rsp[0]['_id']
                                    rcode = True
                                else:
                                    rcode = False
                                    data = 'No such entity found'
                            else:
                                ent_id = ObjectId(ent_id)
                                rcode = True
                        else:
                            rcode = False
                            data = 'No entity id given'
                    else:
                        try:
                            ent_id = self.request.arguments['ent_id']
                        except Exception, e:
                            ent_id = None
                        if(ent_id != None):
                            rcode = False
                            data = 'got ent id implicitly'
                        else:
                            ent_id = entity_id
                            rcode = True
                    if(rcode == True):
                        yield self.devices.insert({"imei": imei, "dev_type": dev_type, "mobile_number": mob_num, "status": "new",
                                                    "entity_id": ent_id})
                        data = 'device added successfully'
                else:
                    rcode = False
                    data = "wrong entity id"
            else:
                rcode = False
                data = "wrong user id"
        resp = {"resp_code": rcode, "data": data}
        self.write(resp)

    @defer.inlineCallbacks
    def delete(self):
        d_id = self.get_arguments('d_id')
        d_id = d_id[0]
        er = yield self.users.find({"_id": ObjectId(self.uid)})
        if len(er):
            if(er[0]['role'] == 'admin'):
                res = yield self.devices.find({"_id": ObjectId(d_id)})
                if len(res):
                    mob_num = res[0]['mobile_number']
                    yield self.devices.remove({"_id": ObjectId(d_id)})
                    rs = yield self.vehicles.find({"dev_id": ObjectId(d_id)})
                    if len(rs):
                        v_id = rs[0]["_id"]
                        dev_id = "Not_assigned"
                        yield self.vehicles.find_and_modify(
                            query = {"_id": v_id},
                            update = {"$set": {"dev_id": dev_id, "driver_number": dev_id}}
                        )
                    rsp = yield self.users.find({"mobile_number": mob_num})
                    if len(rsp):
                        if(rsp[0]['role'] == "driver"):
                            yield self.users.remove({"mobile_number": mob_num})
                        else:
                            log.msg("role is not driver")
                    rcode = True
                    data = 'deleted successfully'
                else:
                    rcode = False
                    data = 'wrong device id'
            else:
                rcode = False
                data = 'operating user is not admin'
        else:
            rcode = False
            data = 'invalid user id'
        resp = {'resp_code': rcode, 'data': data}
        self.write(resp)

    @defer.inlineCallbacks
    def put(self):
        d_id = self.request.arguments['d_id']
	imei = self.request.arguments['imei']
        dev_type = self.request.arguments['dev_type']
        mob_num = self.request.arguments['mob_num']
        res = yield self.devices.find({"_id": ObjectId(d_id)})
        if len(res):
            m_num = res[0]['mobile_number']
            er = yield self.users.find({"_id": ObjectId(self.uid)})
            if len(er):
                entity_id = er[0]['entity_id']
                erp = yield self.entity.find({"_id": entity_id})
                if len(er):
                    ent_name = erp[0]['entity_name']
                    if(ent_name == 'xlayer' or ent_name == 'etrance'):
                        try:
                            ent_id = self.request.arguments['ent_id']
                        except Exception, e:
                            ent_id = None
                        if(ent_id != None):
                            if(str(ent_id) == 'none'):
                                rsp = yield self.entity.find({"entity_name": "xlayer"})
                                if len(rsp):
                                    ent_id = rsp[0]['_id']
                                    rcode = True
                                else:
                                    rcode = False
                                    data = 'No such entity found'
                            else:
                                ent_id = ObjectId(ent_id)
                                rcode = True
                        else:
                            rcode = False
                            data = 'No entity id given'
                    else:
                        try:
                            ent_id = self.request.arguments['ent_id']
                        except Exception, e:
                            ent_id = None
                        if(ent_id != None):
                            rcode = False
                            data = 'got ent id implicitly'
                        else:
                            ent_id = entity_id
                            rcode = True
                    if(rcode == True):
                        yield self.users.find_and_modify(
                            query = {"mobile_number": m_num},
                            update = {"$set": {"entity_id": ent_id}}
                        )
                        if(m_num != mob_num):
                            cur_d_type = res[0]['dev_type']
                            if(cur_d_type == "mobile"):
                                yield self.vehicles.find_and_modify(
                                    query = {"dev_id": ObjectId(d_id)},
                                    update = {"$set": {"driver_number": mob_num}}
                                )
                                yield self.users.find_and_modify(
                                    query = {"mobile_number": m_num, "role": "driver"},
                                    update = {"$set": {"mobile_number": mob_num}}
                                )
                        yield self.devices.find_and_modify(
                            query = {"_id": ObjectId(d_id)},
                            update = {"$set": {"imei": imei, "entity_id": ent_id, "dev_type": dev_type,
                                        "mobile_number": mob_num}}
                        )
                        data = 'updated successfully'
                else:
                    rcode = False
                    data = 'entity not found'
            else:
                rcode = False
                data = 'user not valid'
        else:
            rcode = False
            data = "Invalid device"
        resp = {'resp_code': rcode, 'data': data}
        self.write(resp)

@jwtauth
class NewDeviceDetailsHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    devices = MongoMixin.db.devices
    users = MongoMixin.db.users
    entity = MongoMixin.db.entities

    @defer.inlineCallbacks
    def get(self):
        u_id = self.uid
        rsp = yield self.users.find({"_id": ObjectId(u_id)})
        if len(rsp):
            ent_id = rsp[0]['entity_id']
            if(ent_id == "Not_assigned"):
                resp = {"resp_code": False, "data": "No user data"}
            else:
                res = yield self.entity.find({"_id": ent_id})
                result = []
                if len(res):
                    ent_name = res[0]['entity_name']
                    if(ent_name == 'xlayer' or ent_name == 'etrance'):
                        rs = yield self.devices.find()
                        devs = []
                        if len(rs):
                            for r in rs:
                                if(r['status'] == "new" and r['dev_type'] == 'gps device'):
                                    v = {"device_id": str(r['_id']), "imei": r['imei'], "mobile_number": r['mobile_number'],
                                        "status": r['status'], "device_type": r['dev_type']}
                                else:
                                    continue
                                devs.append(v)
                        res = yield self.users.find({"role": "driver", "vehicles": []})
                        drivers = []
                        if len(res):
                            for r in res:
                                driver_name = r['full_name']
                                v = {"driver_id": str(r['_id']), "driver_name": r["full_name"]}
                                drivers.append(v)
                        v = {"device_list": devs, "driver_list": drivers}
                        result.append(v)
                    else:
                        rs = yield self.devices.find({"entity_id": ent_id})
                        devs = []
                        if len(rs):
                            for r in rs:
                                if(r['status'] == "new" and r['dev_type'] == 'gps device'):
                                    v = {"device_id": str(r['_id']), "imei": r['imei'], "mobile_number": r['mobile_number'],
                                        "status": r['status'], "device_type": r['dev_type']}
                                else:
                                    continue
                                devs.append(v)
                        res = yield self.users.find({"role": "driver", "vehicles": [], "entity_id": ent_id})
                        drivers = []
                        if len(res):
                            for r in res:
                                driver_name = res[0]['full_name']
                                v = {"driver_id": str(res[0]['_id']), "driver_name": res[0]["full_name"]}
                                drivers.append(v)
                        v = {"device_list": devs, "driver_list": drivers}
                        result.append(v)
                resp = {"resp_code": True, "data": result}
        else:
            resp = {"resp_code": False, "data": "data not available"}
        self.write(resp)

@jwtauth
class CurrentDeviceDetailsHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    devices = MongoMixin.db.devices
    entity = MongoMixin.db.entities
    users = MongoMixin.db.users

    @defer.inlineCallbacks
    def get(self):
        u_id = self.uid
        rsp = yield self.users.find({"_id": ObjectId(u_id)})
        if len(rsp):
            ent_id = rsp[0]['entity_id']
            if(ent_id == "Not_assigned"):
                resp = {"resp_code": False, "data": "No user data"}
            else:
                res = yield self.entity.find({"_id": ent_id})
                result = []
                if len(res):
                    ent_name = res[0]['entity_name']
                    if(ent_name == 'xlayer' or ent_name == 'etrance'):
                        rs = yield self.devices.find()
                        if len(rs):
                            for r in rs:
                                res = yield self.entity.find({"_id": r['entity_id']})
                                if len(res):
                                    entity_name = res[0]['entity_name']
                                else:
                                    entity_name = "Not_assigned"
                                if(r['dev_type'] == "gps device"):
                                    v = {"d_id": str(r['_id']), "imei": r['imei'], "phone_number": r['mobile_number'],
                                        "status": r['status'], "entity_name": entity_name}
                                    result.append(v)
                                else:
                                    continue
                    else:
                        rs = yield self.devices.find({"entity_id": ent_id})
                        if len(rs):
                            for r in rs:
                                if(r['dev_type'] == 'gps device'):
                                    v = {"d_id": str(r['_id']), "imei": r['imei'], "phone_number": r['mobile_number'],
                                        "status": r['status'], "entity_name": ent_name}
                                    result.append(v)
                                else:
                                    continue
                resp = {'resp_code': True, 'vehicles': result}
        else:
            resp = {'resp_code': False, 'detail': 'No data available'}
        self.write(resp)
