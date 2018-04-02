import cyclone.web
from twisted.python import log
import os
import getpass
from web_utils import *
from common import *
from jwt_auth import jwtauth
from loc_websocket import *

path = '/home/'+getpass.getuser()+'/tracker/uploads/'
server_url = 'https://localhost:7777'

@jwtauth
class UserHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    users = MongoMixin.db.users

    @defer.inlineCallbacks
    def get(self):
        try:
            u_id = self.get_arguments('u_id')
            u_id = u_id[0]
            rs = yield self.users.find({"_id": ObjectId(self.u_id)})
        except Exception, e:
            print("exception:", e)
            rs = yield self.users.find({"_id": ObjectId(self.uid)})
        if len(rs):
            log.msg("Data are in tables")
            for r in rs:
                ent_id = str(r['entity_id'])
                filepath = path+ent_id
                if os.path.exists(filepath):
                    filename = server_url+'/uploads/'+ent_id+'/'+ent_id+'.png'
                else:
                    filename = server_url+'/uploads/default_profile.png'
                if(r['role'] == 'admin'):
                    v = {"u_id": str(r["_id"]), "username": r["username"], "email_id": r['email_id'],
                        "contact_number": r['mobile_number'], "entity_id": ent_id, 'url': filename}
                else:
                    vehicles = []
                    for x in r["vehicles"]:
                        vehicles.append(str(x))
                    v = {"u_id": str(r["_id"]), "username": r["username"], "email_id": r['email_id'],
                        "contact_number": r['mobile_number'], "vehicle_list": vehicles, "entity_id": ent_id,
                        "url": filename}
            resp = {'resp_code': True, 'user_list': v}
        else:
            resp = {'resp_code': False, 'user_list': "No data available"}
        self.write(resp)

    @defer.inlineCallbacks
    def post(self):
        role = self.request.arguments['role']
        user = self.request.arguments['username']
        password = self.request.arguments['password']
        mob_num = self.request.arguments['mobile_number']
        email_id = self.request.arguments['email_id']
        ent_id = "Not_assigned"
        rs = yield self.users.find({"mobile_number": mob_num})
        if len(rs):
            resp = {'resp_code': False, 'data': "user already exists"}
        else:
            yield self.users.insert({"role": role, "username": user, "mobile_number": mob_num, "password": password,
                                    "email_id": email_id, "vehicles": [], "entity_id": ent_id})
            resp = {"resp_code": True, "data": "new user inserted successfully"}
        self.write(resp)

    @defer.inlineCallbacks
    def delete(self):
        u_id = self.get_arguments("u_id")
        u_id = u_id[0]
        rs = yield self.users.remove({"_id": ObjectId(u_id)})
        log.msg("successfully deleted")
        self.write({'resp_code': True, 'data': 'successfully deleted'})

    @defer.inlineCallbacks
    def put(self):
        u_id = self.request.arguments["u_id"]
        user = self.request.arguments['username']
        mob_num = self.request.arguments['mobile_number']
        role = self.request.arguments['role']
        rs = yield self.users.find_and_modify(
            query = {"_id": ObjectId(u_id)},
            update = {"$set": {"username": user, "mobile_number": mob_num,
                      "role": role, }}
        )
        log.msg("updated successfully")

@jwtauth
class CurrentUserDetailsHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    users = MongoMixin.db.users
    entity = MongoMixin.db.entities
    vehicles = MongoMixin.db.vehicles

    @defer.inlineCallbacks
    def get(self):
        u_id = self.uid
        role = self.get_arguments('role')
        role = role[0]
        es = yield self.users.find({"_id": ObjectId(u_id)})
        if len(es):
            full_name = es[0]['full_name']
            ent_id = es[0]['entity_id']
            esp = yield self.entity.find({"_id": ent_id})
            if len(esp):
                entity_name = esp[0]['entity_name']
                result = []
                if(entity_name == 'xlayer' or entity_name == 'etrance'):
                    rs = yield self.users.find({"role": role})
                    if len(rs):
                        log.msg("Data are in tables")
                        for r in rs:
                            if(role == "user" or role == "driver"):
                                vehicles = []
                                for x in r["vehicles"]:
                                    rp = yield self.vehicles.find({"_id": x})
                                    if len(rp):
                                        reg_num = rp[0]['reg_num']
                                    vehicles.append(reg_num)
                                if(r['entity_id'] != 'Not_assigned'):
                                    rsp = yield self.entity.find({"_id": ObjectId(r['entity_id'])})
                                    if len(rsp):
                                        ent_name = rsp[0]['entity_name']
                                    else:
                                        ent_name = 'None'
                                else:
                                    ent_name = 'None'
                                u_id = str(r["_id"])
                                if(r['role'] == 'user'):
                                    if u_id in user_sockets:
                                        conn_st = True
                                    else:
                                        conn_st = False
                                else:
                                    conn_st = False
                                v = {"u_id": str(r['_id']), "role": r['role'], "username": r["username"], "email_id": r['email_id'],
                                    "contact_number": r['mobile_number'], "vehicle_list": vehicles, "entity_id": str(r['entity_id']),
                                    "full_name": r['full_name'], "entity_name": ent_name, "connection_status": conn_st}
                                result.append(v)
                            elif(role == 'admin'):
                                if(r['entity_id'] != 'Not_assigned'):
                                    rsp = yield self.entity.find({"_id": ObjectId(r['entity_id'])})
                                    if len(rsp):
                                        ent_name = rsp[0]['entity_name']
                                    else:
                                        ent_name = "None"
                                else:
                                    ent_name = "None"
                                v = {"u_id": str(r["_id"]), "role": r['role'], "username": r["username"], "email_id": r['email_id'],
                                    "contact_number": r['mobile_number'], "entity_id": str(r['entity_id']), "entity_name": ent_name,
                                    "full_name": r['full_name']}
                                result.append(v)
                    else:
                        resp = {"resp_code": False, "data": "No user present"}
                else:
                    rs = yield self.users.find({"role": role, "entity_id": ObjectId(ent_id)})
                    if len(rs):
                        for r in rs:
                            if(role == 'user' or role == 'driver'):
                                vehicles = []
                                for x in r["vehicles"]:
                                    rp = yield self.vehicles.find({"_id": x})
                                    if len(rp):
                                        reg_num = rp[0]['reg_num']
                                    else:
                                        reg_num = 'none'
                                    vehicles.append(reg_num)
                                u_id = str(r["_id"])
                                if(r['role'] == 'user'):
                                    if str(r['_id']) in user_sockets:
                                        conn_st = True
                                    else:
                                        conn_st = False
                                else:
                                    conn_st = False
                                v = {"u_id": str(r["_id"]), "role": r['role'], "username": r["username"], "email_id": r['email_id'],
                                    "contact_number": r['mobile_number'], "vehicle_list": vehicles, "entity_id": str(r['entity_id']),
                                    "full_name": r['full_name'], "entity_name": entity_name, "connection_status": conn_st}
                                result.append(v)
                            elif(role == 'admin'):
                                v = {"u_id": str(r["_id"]), "role": r['role'], "username": r["username"], "email_id": r['email_id'],
                                    "contact_number": r['mobile_number'], "entity_id": str(r['entity_id']), "full_name": r['full_name'],
                                    "entity_name": entity_name}
                                result.append(v)
                resp = {'resp_code': True, 'user_list': result}
        else:
            resp = {'resp_code': False, 'user_list': "No data available"}
        self.write(resp)

@jwtauth
class UserInfoHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    users = MongoMixin.db.users
    vehicles = MongoMixin.db.vehicles

    @defer.inlineCallbacks
    def get(self):
        u_id = self.uid
        role = self.get_arguments('role')
        role = role[0]
        rs = yield self.users.find({"_id": ObjectId(u_id)})
        if len(rs):
            if(role == rs[0]['role']):
                vehicle = rs[0]['vehicles']
                if len(vehicle):
                    v_id = vehicle[0]
                    es = yield self.vehicles.find({"_id": v_id})
                    if len(es):
                        result = []
                        if(es[0]['driver_number'] == 'Not_assigned'):
                            dr_num = 'NA'
                        else:
                            dr_num = es[0]['driver_number']
                        v = {"vehicle_id": str(v_id), "reg_num": es[0]['reg_num'], "make": es[0]['make'],
                            "mobile_number": rs[0]['mobile_number'], "color": es[0]['colour'], "full_name": rs[0]['full_name'],
                            "model": es[0]['model'], "email_id": rs[0]['email_id']}
                        result.append(v)
                        rcode = True
                        ecode = 0
                        data = result
                        d_data = result
                    else:
                        rcode = False
                        ecode = 1
                        data = "NDAV"       #no data available
                        d_data = "No data available"
                else:
                    rcode = False
                    ecode = 1
                    data = "UNAV"           # you are not attatched to any vehicle
                    d_data = "You are not assigned to any vehicle"
            else:
                rcode = False
                ecode = 2
                data = "UNDR"       #user is not a driver
                d_data = "This is not a driver account"
        else:
            rcode = False
            ecode = 3
            data = "NULL"
            d_data = "Invalid account"
        if(role == "user"):
            resp = {"resp_code": rcode, "data": data}
        elif(role == "driver"):
            resp = {"resp_code": rcode, "error_code": ecode, "data": d_data}
        else:
            log.msg("got wrong role")
        self.write(resp)

class ChangeUserHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    users = MongoMixin.db.users

    @defer.inlineCallbacks
    def put(self):
        mob_num = self.request.arguments['mobile_number']
        new_num = self.request.arguments['newnumber']
        rs = yield self.users.find_and_modify(
           query = {"mob_num": mob_num},
           update = {"newnumber": new_num}
        )
        self.write({'resp_code': True, 'data': 'successfully updated'})


class AdminHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    users = MongoMixin.db.users

    @defer.inlineCallbacks
    def get(self):
        rs = yield self.users.find()
        result = []
        if len(rs):
            log.msg("Data are in tables")
            for r in rs:
                vehicles = []
                for x in r["vehicles"]:
                    vehicles.append(str(x))
                v = {"u_id": str(r["_id"]), "role": r['role'], "username": r["username"], "email_id": r['email_id'],
                    "contact_number": r["mobile_number"], "vehicle_list": vehicles, "entity_id": str(r['entity_id'])}
                result.append(v)
            resp = {'resp_code': True, 'vehicles': result}
        else:
            resp = {'resp_code': False, 'data': "No data available"}
        self.write(resp)

    @defer.inlineCallbacks
    def post(self):
        role = self.request.arguments['role']
        user = self.request.arguments['username']
        pwd = self.request.arguments['password']
        mob_num = self.request.arguments['mobile_number']
        email_id = self.request.arguments['email_id']
        rs = yield self.users.insert({"role": role, "username": user, "password": pwd, "mobile_number": mob_num,
            "email_id": email_id, "vehicles": [], "entity_id": "Not_assigned"})
        self.write({'resp_code': True, 'data': 'successfully inserted'})
