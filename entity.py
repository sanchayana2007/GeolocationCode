import cyclone.web
from twisted.python import log
import os
import shutil
import getpass
from web_utils import *
from common import *
from vehicles import GetKdbData
from jwt_auth import jwtauth

path = '/home/'+getpass.getuser()+'/tracker/uploads/'

class EntityHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    entity = MongoMixin.db.entities
    users = MongoMixin.db.users
    vehicles = MongoMixin.db.vehicles
    devices = MongoMixin.db.devices
    alarms = MongoMixin.db.alarms

    @defer.inlineCallbacks
    def post(self):
        ent_name = self.request.arguments['entity_name']
        ent_services = self.request.arguments['services']
        owner = self.request.arguments['owner']
        mob_num = self.request.arguments['mobile_number']
        emrge_num = self.request.arguments['emergency_number']
        address = self.request.arguments['address']
        email = self.request.arguments['email_id']
        alt_email = self.request.arguments['alternate_email_id']
        filename = self.request.arguments['filename']
        rs = yield self.entity.find({"entity_name": ent_name})
        if len(rs):
            resp = {"resp_code": False, "data": "entity already present"}
        else:
            services = []
            for x in ent_services:
                services.append(x)
            yield self.entity.insert({"entity_name": ent_name,
                                      "services": services,
                                      "owner": owner,
                                      "mobile_number": mob_num,
                                      "emergency_mobile_number": emrge_num,
                                      "email_id": email,
                                      "address": address,
                                      "alternate_email_id": alt_email})
            es = yield self.entity.find({"entity_name": ent_name})
            if len(es):
                ent_id = es[0]['_id']
            yield self.alarms.insert({"entity_id": ent_id, "alarm_type": "Vehicle breakdown", "count": 0})
            yield self.alarms.insert({"entity_id": ent_id, "alarm_type": "Driver misbehaving", "count": 0})
            yield self.alarms.insert({"entity_id": ent_id, "alarm_type": "Driver overspeeding", "count": 0})
            yield self.alarms.insert({"entity_id": ent_id, "alarm_type": "Person is sick", "count": 0})

            if(filename != "none"):
                temp = path+filename
                f_ext = os.path.basename(temp)
                fname, file_ext = os.path.splitext(f_ext)
                if(file_ext != '.png'):
                    file_ext = '.png'
                filepath = path+str(ent_id)
                if not os.path.exists(filepath):
                    log.msg("creating directory")
                    os.makedirs(filepath)
                fname = str(ent_id)+file_ext
                curr_file = filepath+'/'+fname
                os.rename(temp, curr_file)
            else:
                log.msg("ignoring logo upload")
            resp = {"resp_code": True, "data": "inserted successfully"}
            self.write(resp)

    @defer.inlineCallbacks
    def delete(self):
        ent_id = self.get_arguments('ent_id')
        ent_id = ent_id[0]
        es = yield self.entity.find({"entity_name": "xlayer"})
        if len(es):
            et_id = es[0]['_id']
        else:
            et_id = "Not_assigned"
        rs = yield self.entity.remove({"_id": ObjectId(ent_id)})
        yield self.users.find_and_modify(
            query = {"entity_id": ObjectId(ent_id)},
            update = {"$set": {"entity_id": et_id}}
        )
        yield self.vehicles.find_and_modify(
            query = {"entity_id": ObjectId(ent_id)},
            update = {"$set": {"entity_id": et_id}}
        )
        yield self.devices.find_and_modify(
            query = {"entity_id": ObjectId(ent_id)},
            update = {"$set": {"entity_id": et_id}}
        )
        yield self.alarms.remove({"entity_id": ObjectId(ent_id)})
        filepath = path+str(ent_id)
        if os.path.exists(filepath):
            shutil.rmtree(filepath)
            log.msg("logo folder has been deleted")
        else:
            log.msg("entity had no logo")
        if len(rs):
            resp = {"resp_code": True, "data": "deleted successfully"}
        else:
            resp = {"resp_code": False, "data": "delete failed"}
        self.write(resp)

    @defer.inlineCallbacks
    def put(self):
        ent_id = self.request.arguments['ent_id']
        ent_name = self.request.arguments['entity_name']
        ent_services = self.request.arguments['services']
        owner = self.request.arguments['owner']
        cont_num = self.request.arguments['mobile_number']
        emrge_num = self.request.arguments['emergency_number']
        address = self.request.arguments['address']
        email = self.request.arguments['email_id']
        filename = self.request.arguments['filename']
        alternate_email = self.request.arguments['alternate_email_id']
        services = []
        for x in ent_services:
            services.append(x)
        rs = yield self.entity.find_and_modify(
                query = {"_id": ObjectId(ent_id)},
                update = {"$set": {"entity_name": ent_name, "owner": owner, "mobile_number": cont_num,
                            "emergency_mobile_number": emrge_num,"address": address, "email_id": email,
                            "alternate_email_id": alternate_email, "services": services}}
            )
        if(filename != 'none'):
            temp = path+filename
            f_ext = os.path.basename(temp)
            fname, file_ext = os.path.splitext(f_ext)
            if(file_ext != '.png'):
                file_ext = '.png'
            filepath = path+ent_id
            fname = ent_id+file_ext
            if os.path.exists(filepath):
                log.msg("deleting existing file from directory")
                os.remove(filepath+'/'+fname)
            else:
                log.msg("making directory")
                os.makedirs(filepath)
            curr_file = filepath+'/'+fname
            os.rename(temp, curr_file)
        if len(rs):
            resp = {"resp_code": True, "data": "updated successfully"}
        else:
            resp = {"resp_code": False, "data": "update failed"}
        self.write(resp)

class EntityLogoUploadHandler(cyclone.web.RequestHandler, MongoMixin):
    SUPPORTED_METHODS = ('GET', 'POST', 'DELETE', 'PUT')

    def post(self):
        fileinfo = self.request.files['file'][0]
        fname = fileinfo['filename']
        fh = open(path+fname, 'w')
        fh.write(fileinfo['body'])
        fh.close()
        resp = {"resp_code": True, "data": "file uploaded succesfully"}
        self.write(resp)

class CurrentEntityDetailsHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ('GET', 'POST', 'DELETE', 'PUT')
    entity = MongoMixin.db.entities

    @defer.inlineCallbacks
    def get(self):
        rs = yield self.entity.find()
        result = []
        if len(rs):
            for r in rs:
                v = {"entity_id": str(r['_id']), "entity_name": r['entity_name'], "owner_name": r['owner'],
                     "contact_number": r['mobile_number'], "emergency_number": r['emergency_mobile_number'],
                     "email_id": r['email_id'], "alternate_email_id": r['alternate_email_id'],
                     "address": r['address']}
                result.append(v)
            resp = {"resp_code": True, "entity_data": result}
        else:
            resp = {"resp_code": False, "entity_data": "no data available"}
        self.write(resp)

@jwtauth
class AllEntityVehicleDetailsHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ('GET', 'POST', 'DELETE', 'PUT')
    users = MongoMixin.db.users
    vehicles = MongoMixin.db.vehicles
    entity = MongoMixin.db.entities
    get_data = GetKdbData()

    @defer.inlineCallbacks
    def get(self):
        u_id = self.uid
        rs = yield self.users.find({"_id": ObjectId(u_id)})
        if len(rs):
            result = []
            if(rs[0]["role"] == "admin"):
                ent_id = rs[0]['entity_id']
                if(ent_id == "Not_assigned"):
                    rcode = False,
                    data = "ETNA"                           #ETNA: entity not assigned
                else:
                    esp = yield self.entity.find({"_id": ent_id})
                    if len(esp):
                        ent_name = esp[0]['entity_name']
                        if(ent_name == 'etrance' or ent_name == 'xlayer'):
                            res = yield self.vehicles.find()
                            if len(res):
                                vehicles = []
                                for r in res:
                                    topic = 'loc:' + str(r['_id'])
                                    data = yield self.get_data.kdb_get_data(topic, 0, 0)
                                    if(data == 'NULL'):
                                        loc_resp = []
                                    else:
                                        loc_resp = data
                                    if len(loc_resp):
                                        ulat = float(loc_resp[0]['latitude'])
                                        ulong = float(loc_resp[0]['longitude'])
                                        ts = int(loc_resp[0]['timestamp'])
                                        status = True
                                    else:
                                        status = False
                                        ulat = 0
                                        ulong = 0
                                        ts = 0
                                    us = yield self.users.find({"vehicles": [r['_id']]})
                                    if len(us):
                                        for x in us:
                                            if(x['role'] == "driver"):
                                                dr_name = x['full_name']
                                                break
                                            else:
                                                dr_name = "NA"
                                    else:
                                        dr_name = "NA"
                                    v = {"vehicle_id": str(r['_id']),
                                        "reg_num": r['reg_num'],
                                        "make": r['make'],
                                        "model": r['model'],
                                        "color": r['colour'],
                                        "driver_name": dr_name,
                                        "driver_number": r['driver_number'],
                                        "status": status,
                                        "latitude": ulat,
                                        "longitude": ulong,
                                        "time_stamp": ts,
                                        "device_id": str(r['dev_id'])}
                                    vehicles.append(v)
                                rcode = True
                                data = vehicles
                            else:
                                rcode = False
                                data = "NDAV"
                        else:
                            res = yield self.vehicles.find({"entity_id": ent_id})
                            if len(res):
                                vehicles = []
                                for r in res:
                                    topic = 'loc:' + str(r['_id'])
                                    data = yield self.get_data.kdb_get_data(topic, 0, 0)
                                    if(data == "NULL"):
                                        loc_resp = []
                                    else:
                                        loc_resp = data
                                    if len(loc_resp):
                                        ulat = float(loc_resp[0]['latitude'])
                                        ulong = float(loc_resp[0]['longitude'])
                                        ts = loc_resp[0]['timestamp']
                                        status = True
                                    else:
                                        status = False
                                        ulat = 0
                                        ulong = 0
                                        ts = 0
                                    us = yield self.users.find({"vehicles": [r['_id']]})
                                    if len(us):
                                        for x in us:
                                            if(x['role'] == "driver"):
                                                dr_name = x['full_name']
                                                break
                                            else:
                                                dr_name = "NA"
                                    else:
                                        dr_name = "NA"
                                    v = {"vehicle_id": str(r['_id']),
                                        "reg_num": r['reg_num'],
                                        "make": r['make'],
                                        "model": r['model'],
                                        "color": r['colour'],
                                        "driver_name": dr_name,
                                        "driver_number": r['driver_number'],
                                        "status": status,
                                        "latitude": ulat,
                                        "longitude": ulong,
                                        "time_stamp": ts,
                                        "device_id": str(r['dev_id'])}
                                    vehicles.append(v)
                                rcode = True
                                data = vehicles
                            else:
                                rcode = False
                                data =  "NDAV"                      #NDAV: no data available
                    else:
                        rcode = False
                        data = "NDAV"
            else:
                rcode = False
                data = "UNAD"                               #UNAD: user not an admin
        else:
            rcode = False
            data = "NULL"                                   #NULL: user does not exist
        resp = {"resp_code": rcode, "data": data}
        self.write(resp)

