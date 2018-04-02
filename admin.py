import cyclone.web
from twisted.python import log
from web_utils import *
from common import *
import time
from jwt_auth import jwtauth

#@jwtauth
class CreateUserHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    users = MongoMixin.db.users
    devices = MongoMixin.db.devices
    vehicles = MongoMixin.db.vehicles
    entity = MongoMixin.db.entities

    @defer.inlineCallbacks
    def post(self):
        log.msg(self.request)
        #print(self.request)
        role = self.request.arguments['role']
        full_name = self.request.arguments['full_name']
        user = self.request.arguments['username']
        mob_num = self.request.arguments['mobile_number']
        email = self.request.arguments['email_id']
        v_id = self.request.arguments['v_id']
        t = int(time.time())
        rs = yield self.users.find({"mobile_number": mob_num})
        if len(rs):
            rcode = False
            data = 'user already exists'
        else:
            er = yield self.users.find({"_id": ObjectId(self.uid)})
            if len(er):
                entity_id = er[0]['entity_id']
                erp = yield self.entity.find({"_id": entity_id})
                if len(erp):
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
                        if(str(v_id) == 'none'):
                            vehicle = []
                            rcode = True
                        else:
                            rsp = yield self.vehicles.find({"_id": ObjectId(v_id)})
                            if len(rsp):
                                if(role == 'driver'):
                                    ep = yield self.users.find({"vehicles": [ObjectId(v_id)], "role": role, "entity_id": entity_id})
                                    if len(ep):
                                        vehicle = []
                                        rcode = True
                                    else:
                                        vehicle = [ObjectId(v_id)]
                                        rcode = True
                                else:
                                    vehicle = [ObjectId(v_id)]
                                    rcode = True
                            else:
                                vehicle = []
                                rcode = True
                        if(role != 'driver'):
                            yield self.users.insert({"role": role, "full_name": full_name, "username": user,
                                    "password": "1234","mobile_number": mob_num,"email_id": email, "vehicles": vehicle,
                                    "entity_id": ent_id, "l_latitude": "12.9151","l_longitude": "77.6454", "l_update_time": t})
                            data = 'user was added successfully'
                        else:
                            er = yield self.devices.find({"mobile_number": mob_num})
                            if len(er):
                                rcode = False
                                data = "device already exists"
                            else:
                                yield self.users.insert({"role": role, "full_name": full_name, "username": user,
                                        "password": "1234","mobile_number": mob_num,"email_id": email, "vehicles": vehicle,
                                        "entity_id": ent_id, "l_latitude": "12.9151","l_longitude": "77.6454", "l_update_time": t})
                                yield self.devices.insert({"imei": "unknown", "dev_type": "mobile", "status": "new",
                                        "mobile_number": mob_num, "entity_id": ent_id})
                                if len(vehicle):
                                    ems = yield self.devices.find({"mobile_number": mob_num})
                                    if len(ems):
                                        dev_id = ems[0]['_id']
                                        yield self.devices.find_and_modify(
                                            query = {"_id": dev_id},
                                            update = {"$set": {"status": "attached"}}
                                        )
                                        yield self.vehicles.find_and_modify(
                                            query = {"_id": ObjectId(vehicle[0])},
                                            update = {"$set": {"driver_number": mob_num, "dev_id": dev_id}}
                                        )
                                data = 'user was added successfully'
                else:
                    rcode = False
                    data = 'invalid entity'
            else:
                rcode = False
                data = 'wrong user id'
        resp = {'resp_code': rcode, 'data': data}
        self.write(resp)

    @defer.inlineCallbacks
    def delete(self):
        u_id = self.get_arguments('u_id')
        u_id = u_id[0]
        er = yield self.users.find({"_id": ObjectId(self.uid)})
        if len(er):
            if(er[0]['role'] == 'admin'):
                res = yield self.users.find({"_id": ObjectId(u_id)})
                if len(res):
                    if(res[0]['role'] == "driver"):
                        mob_num = res[0]['mobile_number']
                    else:
                        mob_num = "NA"
                    yield self.users.remove({"_id": ObjectId(u_id)})
                    rsp = yield self.devices.find({"mobile_number": mob_num})
                    if len(rsp):
                        dev_id = rsp[0]['_id']
                        yield self.devices.remove({"mobile_number": mob_num})
                        yield self.vehicles.find_and_modify(
                            query = {"dev_id": dev_id},
                            update = {"$set": {"dev_id": "Not_assigned", "driver_number": "Not_assigned"}}
                        )
                    else:
                        log.msg('user was not driver')
                    rcode = True
                    data = "delete successful"
                else:
                    rcode = False
                    data = 'NULL'
            else:
                rcode = False
                data = 'operating user is not admin'
        else:
            rcode = False
            data = 'got wrong user id'
        resp = {'resp_code': rcode, 'data': data}
        self.write(resp)

    @defer.inlineCallbacks
    def put(self):
        u_id = self.request.arguments['u_id']
        v_id = self.request.arguments['v_id']
        role = self.request.arguments['role']
        full_name = self.request.arguments['full_name']
        username = self.request.arguments['username']
        mob_num = self.request.arguments['mobile_number']
        email = self.request.arguments['email_id']

        rs = yield self.users.find({"_id": ObjectId(u_id)})
        if len(rs):
            ex_v_id = rs[0]['vehicles']
            er = yield self.users.find({"_id": ObjectId(self.uid)})
            if len(er):
                entity_id = er[0]['entity_id']
                m_num = rs[0]['mobile_number']
                if(rs[0]["role"] == "admin"):
                    rcode = False
                    data = 'admin has no vehicle'
                else:
                    vehicles = rs[0]['vehicles']
                    if len(vehicles):
                        if(str(v_id) == 'none'):
                            v_id = []
                            rcode = True
                        else:
                            flag = 0
                            for x in vehicles:
                                if(x == ObjectId(v_id)):
                                    flag = 1
                                    break
                                continue
                            v_id = [ObjectId(v_id)]
                            if not flag:
                                if(rs[0]['role'] == 'driver'):
                                    em = yield self.users.find({"role": "driver", "vehicles": v_id})
                                    if len(em):
                                        rcode = True
                                        v_id = []
                                    else:
                                        rcode = True
                                else:
                                    rcode = True
                    else:
                        if(str(v_id) == 'none'):
                            v_id = []
                            rcode = True
                        else:
                            if(rs[0]['role'] == 'driver'):
                                em = yield self.users.find({"role": "driver", "vehicles": [ObjectId(v_id)]})
                                if len(em):
                                    rcode = True
                                    v_id = []
                                else:
                                    v_id = [ObjectId(v_id)]
                                    rcode = True
                            else:
                                v_id = [ObjectId(v_id)]
                                rcode = True
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
                        query = {"_id": ObjectId(u_id)},
                        update = {"$set": {"full_name": full_name, "username": username,
                                    "role": role, "mobile_number": mob_num, "email_id": email,
                                    "entity_id": ent_id, "vehicles": v_id}}
                    )
                    if(rs[0]['role'] == 'driver'):
                        if(m_num != mob_num):
                            esp = yield self.devices.find({"mobile_number": m_num})
                            if len(esp):
                                d_st = esp[0]['status']
                                if(d_st == 'attached'):
                                    yield self.vehicles.find_and_modify(
                                        query = {"driver_number": m_num},
                                        update = {"$set": {"driver_number": mob_num}}
                                    )
                                else:
                                    log.msg("device is new")
                                yield self.devices.find_and_modify(
                                    query = {"mobile_number": m_num},
                                    update = {"$set": {"mobile_number": mob_num}}
                                )
                        else:
                            if len(v_id):
                                esp = yield self.devices.find({"mobile_number": mob_num})
                                if len(esp):
                                    d_st = esp[0]['status']
                                    if(d_st == 'new'):
                                        yield self.vehicles.find_and_modify(
                                            query = {"_id": v_id[0]},
                                            update = {"$set": {"dev_id": esp[0]['_id'], "driver_number": mob_num}}
                                        )
                                        yield self.devices.find_and_modify(
                                            query = {"mobile_number": mob_num},
                                            update = {"$set": {"status": "attached"}}
                                        )
                                    else:
                                        yield self.vehicles.find_and_modify(
                                            query = {"_id": ex_v_id[0]},
                                            update = {"$set": {"dev_id": "Not_assigned", "driver_number": "Not_assigned"}}
                                        )
                                        yield self.vehicles.find_and_modify(
                                            query = {"_id": v_id[0]},
                                            update = {"$set": {"dev_id": esp[0]['_id'], "driver_number": mob_num}}
                                        )
                                        log.msg('device is already attached')
                            else:
                                if len(ex_v_id):
                                    emp = yield self.vehicles.find({"_id": ex_v_id[0]})
                                    if len(emp):
                                        yield self.vehicles.find_and_modify(
                                            query = {"_id": ex_v_id[0]},
                                            update = {"$set": {"driver_number": "Not_assigned", "dev_id": "Not_assigned"}}
                                        )
                                        yield self.devices.find_and_modify(
                                            query = {"_id": emp[0]['dev_id']},
                                            update = {"$set": {"status": "new"}}
                                        )
                                else:
                                    log.msg('user had no vehicle previously')
                    if(rs[0]['role'] == 'driver'):
                        yield self.devices.find_and_modify(
                            query = {"mobile_number": m_num},
                            update = {"$set": {"entity_id": ObjectId(ent_id)}}
                        )
                    rcode = True
                    data = "user updated"
            else:
                rcode = False
                data = 'wrong admin id'
        else:
            rcode = False
            data = 'wrong id given'
        resp = {"resp_code": rcode, "data": data}
        self.write(resp)

@jwtauth
class AddVehicleHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    users = MongoMixin.db.users
    vehicles = MongoMixin.db.vehicles
    devices = MongoMixin.db.devices
    entity = MongoMixin.db.entities

    @defer.inlineCallbacks
    def post(self):
        reg_num = self.request.arguments['reg_num']
        maker = self.request.arguments['make']
        model = self.request.arguments['model']
        colour = self.request.arguments['colour']
        drv_id = self.request.arguments['driver_id']
        dev_type = self.request.arguments['dev_type']
        rs = yield self.vehicles.find({"reg_num": reg_num})
        if len(rs):
            rcode = False
            data = 'reg_num is already registered'
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
                        if(dev_type == "mobile"):
                            if(str(drv_id) != 'none'):
                                res = yield self.users.find({"_id": ObjectId(drv_id)})
                                if len(res):
                                    mob_num = res[0]['mobile_number']
                                    drv_id = ObjectId(drv_id)
                                    ep = yield self.devices.find({"mobile_number": mob_num})
                                    if len(ep):
                                        dev_id = ep[0]['_id']
                                    else:
                                        rcode = False
                                        data = "Driver has no device"
                                else:
                                    rcode = False
                                    data = "Invalid driver"
                            else:
                                dev_id = "Not_assigned"
                                mob_num = "Not_assigned"
                                rcode = True
                        elif(dev_type == "gps_device"):
                            gps_id = self.request.arguments['gps_id']
                            if(drv_id == 'none' and gps_id == 'none'):
                                drv_id = 'Not_assigned'
                                dev_id = "Not_assigned"
                                mob_num = "Not_assigned"
                                rcode = True
                            elif(drv_id == "none" and gps_id != 'none'):
                                drv_id = "Not_assigned"
                                mob_num = "Not_assigned"
                                dev_id = ObjectId(gps_id)
                                rcode =True
                            elif(drv_id != 'none' and gps_id == 'none'):
                                res = yield self.users.find({"_id": ObjectId(drv_id)})
                                if len(res):
                                    mob_num = res[0]['mobile_number']
                                    drv_id = ObjectId(drv_id)
                                    dev_id = "Not_assigned"
                                    rcode = True
                                else:
                                    rcode = False
                                    data = "invalid driver id"
                            elif(drv_id != 'none' and gps_id != 'none'):
                                er = yield self.users.find({"_id": ObjectId(drv_id)})
                                if len(er):
                                    mob_num = er[0]['mobile_number']
                                    drv_id = ObjectId(drv_id)
                                    res = yield self.devices.find({"_id": ObjectId(gps_id)})
                                    if len(res):
                                        dev_id = res[0]['_id']
                                        rcode = True
                                    else:
                                        rcode = False
                                        data = "invalid gps id"
                                else:
                                    rcode = False
                                    rcode = "invalid driver id"
                            else:
                                if(drv_id == 'none'):
                                    drv_id = 'Not_assigned'
                                    mob_num = 'Not_assigned'
                                    dev_id = 'Not_assigned'
                                    rcode = True
                                else:
                                    res = yield self.users.find({"_id": ObjectId(drv_id)})
                                    if len(res):
                                        mob_num = res[0]['mobile_number']
                                        drv_id = ObjectId(drv_id)
                                        rcode = True
                                    else:
                                        rcode = False
                                        data = 'invalid driver id'
                        else:
                            if(drv_id == 'none'):
                                drv_id = "Not_assigned"
                                dev_type = "Not_assigned"
                                dev_id = "Not_assigned"
                                mob_num = "Not_assigned"
                                rcode = True
                            else:
                                er = yield self.users.find({"_id": ObjectId(drv_id)})
                                if len(er):
                                    mob_num = er[0]['mobile_number']
                                    drv_id = ObjectId(drv_id)
                                    dev_type = "Not_assigned"
                                    dev_id = "Not_assigned"
                                    rcode = True
                                else:
                                    rcode = False
                                    data = "invalid driver id"
                        if(rcode == True):
                            yield self.vehicles.insert({"reg_num": reg_num, "make": maker, "model": model,
                                "colour": colour, "dev_id": dev_id, "driver_number": mob_num, "entity_id": ent_id,
                                "start_time": 0, "driver_id": drv_id, "dev_type": dev_type})
                            if(dev_id != 'Not_assigned'):
                                yield self.devices.find_and_modify(
                                    query = {"_id": dev_id},
                                    update = {"$set": {"status": "attached"}}
                                )
                            if(str(drv_id) != "none"):
                                es = yield self.vehicles.find({"reg_num": reg_num})
                                if len(es):
                                    yield self.users.find_and_modify(
                                        query = {"_id": ObjectId(drv_id)},
                                        update = {"$set": {"vehicles": [es[0]['_id']]}}
                                    )
                            data = 'added successfully'
                else:
                    rcode = False
                    data = 'invalid entity'
            else:
                rcode = False
                data = 'invalid user id'
        resp = {"resp_code": rcode, "data": data}
        self.write(resp)


    @defer.inlineCallbacks
    def delete(self):
        v_id = self.get_arguments('v_id')
        v_id = v_id[0]
        er = yield self.users.find({"_id": ObjectId(self.uid)})
        if len(er):
            if(er[0]['role'] == 'admin'):
                res = yield self.vehicles.find({"_id": ObjectId(v_id)})
                if len(res):
                    device_id = res[0]['dev_id']
                    yield self.vehicles.remove({"_id": ObjectId(v_id)})
                    rs = yield self.users.find({"vehicles": [ObjectId(v_id)]})
                    if len(rs):
                        for r in rs:
                            u_id = r["_id"]
                            yield self.users.find_and_modify(
                                query = {"_id": ObjectId(u_id)},
                                update = {"$set": {"vehicles":  []}}
                            )
                    if(device_id != "Not_assigned"):
                        yield self.devices.find_and_modify(
                            query = {"_id": ObjectId(device_id)},
                            update = {"$set": {"status": "new"}}
                        )
                rcode = True
                data = 'deleted successfully'
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
        v_id = self.request.arguments['v_id']
        drv_id = self.request.arguments['driver_id']
        dev_type = self.request.arguments['dev_type']
        reg_num = self.request.arguments['reg_num']
        make = self.request.arguments['make']
        model = self.request.arguments['model']
        clr = self.request.arguments['colour']

        rs = yield self.vehicles.find({"_id": ObjectId(v_id)})
        if len(rs):
            dev_id = rs[0]['dev_id']
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
                        if(dev_type == 'mobile'):
                            if(str(drv_id) == 'none'):
                                yield self.devices.find_and_modify(
                                    query = {'_id': dev_id},
                                    update = {'$set': {'status': "new"}}
                                )
                                if(rs[0]['driver_id'] != "Not_assigned"):
                                    yield self.users.find_and_modify(
                                        query = {"_id": rs[0]['driver_id']},
                                        update = {"$set": {"vehicles": []}}
                                    )
                                drv_id = 'Not_assigned'
                                mob_num = 'Not_assigned'
                                dev_id = 'Not_assigned'
                                rcode = True
                            else:
                                res = yield self.users.find({"_id": ObjectId(drv_id)})
                                if len(res):
                                    mob_num = res[0]['mobile_number']
                                    er = yield self.devices.find({"mobile_number": mob_num})
                                    if len(er):
                                        if(drv_id != str(rs[0]['driver_id'])):
                                            yield self.devices.find_and_modify(
                                                query = {"_id": dev_id},
                                                update = {"$set": {"status": "new"}}
                                            )
                                            yield self.devices.find_and_modify(
                                                query = {"_id": er[0]['_id']},
                                                update = {"$set": {"status": "attached"}}
                                            )
                                            yield self.users.find_and_modify(
                                                query = {"_id": rs[0]['driver_id']},
                                                update = {"$set": {"vehicles": []}}
                                            )
                                            yield self.users.find_and_modify(
                                                query = {"_id": ObjectId(drv_id)},
                                                update = {"$set": {"vehicles": [ObjectId(v_id)]}}
                                            )
                                            drv_id = ObjectId(drv_id)
                                            dev_id = er[0]['_id']
                                            rcode = True
                                    else:
                                        rcode = False
                                        data = "device not found"
                                else:
                                    rcode = False
                                    data = "driver not found"
                        elif(dev_type == "gps_device"):
                            gps_id = self.request.arguments['gps_id']
                            if(drv_id == 'none' and gps_id == 'none'):
                                yield self.devices.find_and_modify(
                                    query = {"_id": dev_id},
                                    update = {"$set": {"status": "new"}}
                                )
                                yield self.users.find_and_modify(
                                    query = {"_id": rs[0]['driver_id']},
                                    update = {"$set": {"vehicles": []}}
                                )
                                drv_id = 'Not_assigned'
                                mob_num = 'Not_assigned'
                                dev_id = 'Not_assigned'
                                rcode = True
                            elif(drv_id == 'none' and gps_id != 'none'):
                                res = yield self.devices.find({"_id": ObjectId(gps_id)})
                                if len(res):
                                    yield self.devices.find_and_modify(
                                        query = {"_id": dev_id},
                                        update = {"$set": {"status": "new"}}
                                    )
                                    yield self.devices.find_and_modify(
                                        query = {"_id": ObjectId(gps_id)},
                                        update = {"$set": {"status": "attached"}}
                                    )
                                    if(drv_id != str(rs[0]['driver_id'])):
                                        yield self.users.find_and_modify(
                                            query = {"_id": rs[0]['driver_id']},
                                            update = {"$set": {"vehicles": []}}
                                        )
                                    drv_id = 'Not_assigned'
                                    mob_num = 'Not_assigned'
                                    dev_id = ObjectId(gps_id)
                                    rcode = True
                                else:
                                    rcode = False
                                    data = "invalid gps id"
                            elif(drv_id != 'none' and gps_id == 'none'):
                                er = yield self.users.find({"_id": ObjectId(drv_id)})
                                if len(er):
                                    mob_num = er[0]['mobile_number']
                                    yield self.devices.find_and_modify(
                                        query = {"_id": dev_id},
                                        update = {"$set": {"status": "new"}}
                                    )
                                    if(drv_id != str(rs[0]['driver_id'])):
                                        yield self.users.find_and_modify(
                                            query = {"_id": rs[0]['driver_id']},
                                            update = {"$set": {"vehicles": []}}
                                        )
                                    yield self.users.find_and_modify(
                                        query = {"_id": ObjectId(drv_id)},
                                        update = {"$set": {"vehicles": [ObjectId(v_id)]}}
                                    )
                                    drv_id = ObjectId(drv_id)
                                    dev_id = "Not_assigned"
                                    rcode = True
                                else:
                                    rcode = False
                                    data = "invalid driver id"
                            elif(drv_id != 'none' and gps_id != 'none'):
                                er = yield self.users.find({"_id": ObjectId(drv_id)})
                                if len(er):
                                    mob_num = er[0]['mobile_number']
                                    yield self.devices.find_and_modify(
                                        query = {"_id": dev_id},
                                        update = {"$set": {"status": "new"}}
                                    )
                                    yield self.devices.find_and_modify(
                                        query = {"_id": ObjectId(gps_id)},
                                        update = {"$set": {"status": "attached"}}
                                    )
                                    if(drv_id != str(rs[0]['driver_id'])):
                                        yield self.users.find_and_modify(
                                            query = {"_id": rs[0]['driver_id']},
                                            update = {"$set": {"vehicles": []}}
                                        )
                                    yield self.users.find_and_modify(
                                        query = {"_id": ObjectId(drv_id)},
                                        update = {"$set": {"vehicles": [ObjectId(v_id)]}}
                                    )
                                    drv_id = ObjectId(drv_id)
                                    dev_id = ObjectId(gps_id)
                                    rcode = True
                                else:
                                    rcode = False
                                    data = "invalid driver id"
                            else:
                                if(drv_id == 'none'):
                                    yield self.devices.find_and_modify(
                                        query = {"_id": dev_id},
                                        update = {"$set": {"status": "new"}}
                                    )
                                    yield self.users.find_and_modify(
                                        query = {"_id": rs[0]['driver_id']},
                                        update = {"$set": {"vehicles": []}}
                                    )
                                    dev_id = 'Not_assigned'
                                    drv_id = 'Not_assigned'
                                    mob_num = 'Not_assigned'
                                    rcode = True
                                else:
                                    res = yield self.users.find({"_id": ObjectId(drv_id)})
                                    if len(res):
                                        mob_num = res[0]['mobile_number']
                                        yield self.vehicles.find_and_modify(
                                            query = {"_id": ObjectId(v_id)},
                                            update = {"$set": {"driver_id": ObjectId(drv_id), "dev_id": "Not_assigned",
                                                        "driver_number": mob_num}}
                                        )
                                        if(drv_id != str(rs[0]['driver_id'])):
                                            yield self.users.find_and_modify(
                                                query = {"_id": rs[0]['driver_id']},
                                                update = {"$set": {"vehicles": []}}
                                            )
                                        yield self.users.find_and_modify(
                                            query = {"_id": ObjectId(drv_id)},
                                            update = {"$set": {"vehicles": [ObjectId(v_id)]}}
                                        )
                                        dev_id = "Not_assigned"
                                        drv_id = ObjectId(drv_id)
                                        rcode = True
                                    else:
                                        rcode = False
                                        data = "invalid driver id"
                        if(dev_type == 'none'):
                            if(drv_id == 'none'):
                                yield self.users.find_and_modify(
                                    query = {"_id": rs[0]['driver_id']},
                                    update = {"$set": {"vehicles": []}}
                                )
                                yield self.devices.find_and_modify(
                                    query = {"_id": rs[0]['dev_id']},
                                    update = {"$set": {"status": "new"}}
                                )
                                dev_id = "Not_assigned"
                                dev_type = "Not_assigned"
                                drv_id = "Not_assigned"
                                mob_num = "Not_assigned"
                                rcode = True
                            else:
                                if(drv_id != 'None' and drv_id != rs[0]['driver_id']):
                                    er = yield self.users.find({"_id": ObjectId(drv_id)})
                                    if len(er):
                                        mob_num = er[0]['mobile_number']
                                        yield self.users.find_and_modify(
                                            query = {"_id": rs[0]['driver_id']},
                                            update = {"$set": {"vehicles": []}}
                                        )
                                        yield self.users.find_and_modify(
                                            query = {"_id": ObjectId(drv_id)},
                                            update = {"$set": {"vehicles": [ObjectId(v_id)]}}
                                        )
                                        yield self.devices.find_and_modify(
                                            query = {"_id": rs[0]['dev_id']},
                                            update = {"$set": {"status": "new"}}
                                        )
                                        dev_id = "Not_assigned"
                                        dev_type = "Not_assigned"
                                        drv_id = ObjectId(drv_id)
                                        rcode = True
                                    else:
                                        rcode = False
                                        data = "invalid driver id"
                        if(rcode == True):
                            yield self.vehicles.find_and_modify(
                                query = {"_id": ObjectId(v_id)},
                                update = {"$set": {"reg_num": reg_num, "make": make, "model": model,
                                            "colour": clr, "entity_id": ent_id, "driver_id": drv_id, 
                                            "driver_number": mob_num, "dev_id": dev_id, "dev_type": dev_type}}
                            )
                            data = 'updated successfully'
                else:
                    rcode = False
                    data = 'invalid entity'
            else:
                rcode = False
                data = 'invalid user id'
        else:
            rcode = False
            data = 'invalid vehicle id'
        resp = {"resp_code": rcode, "data": data}
        log.msg(resp)
        self.write(resp)


