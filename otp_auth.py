import cyclone.web
import cyclone.httpclient
from twisted.python import log
from web_utils import *
from common import *
from vehicles import GetKdbData
import jwt
import datetime
from jwt_auth import jwtauth, get_token
import sendotp
import time
from geopy.geocoders import Nominatim
from random import randint
from bson.objectid import ObjectId
from loc_websocket import *

authkey = "190375A1kUEbKcBP5a4641be"
message = "TrackiGa verification code(OTP) is"
sender = "TRACKI"

otpobj = sendotp.sendotp(authkey, message+' '+'{{otp}}.')


class OtpAuthInitiateHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    users = MongoMixin.db.users
    otps = MongoMixin.db.otps

    @defer.inlineCallbacks
    def post(self):
        mob_num = self.request.arguments['mobile_number']
        print(mob_num)
        auth = yield self.users.find({"mobile_number": mob_num})
        if auth:
            otp = randint(1000, 9999)
            timestamp = int(time.time())
            rs = yield self.otps.find({"mobile_numer": mob_num})
            if(len(rs) < 1):
                print("New OTP")
            else:
                print("Updating OTP")
                yield self.otps.remove({"mobile_numer": mob_num})
            yield self.otps.insert({"time": timestamp, "mobile_numer": mob_num, "otp": otp})
            print(otp)
            mob_num = '91'+mob_num
            gresp = yield otpobj.send(mob_num, sender, otp)
            print("gresp:%r"%gresp)
            log.msg("valid user")
            resp = {"resp_code": True}
        else:
            log.msg("Invalid user")
            resp = {"resp_code": False, "data": "Invalid User"}
        self.write(resp)


class OtpAuthValidateHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    users = MongoMixin.db.users
    otps = MongoMixin.db.otps

    @defer.inlineCallbacks
    def post(self):
        mob_num = self.request.arguments['mobile_number']
        otp_val = self.request.arguments['otp']
        print(mob_num)
        print(otp_val)
        rs = yield self.otps.find({"mobile_numer": mob_num})
        if(len(rs) < 1):
            response = {"resp_code": False, "data": "number not found"}
        else:
            if(int(otp_val) == rs[0]["otp"]):
                auth = yield self.users.find({"mobile_number": mob_num})
                if len(auth):
                    u_id = ObjectId(auth[0]["_id"])
                    self.token = get_token(u_id)
                    response = {'resp_code': True, 'token': self.token, 'role': auth[0]["role"]}
                    log.msg("Login successfully!")
                    yield self.otps.remove({"mobile_numer": mob_num})
                else:
                    log.msg("New user")
            else:
                log.msg("Wrong OTP entered.")
                response = {"resp_code": False, "data": "wrong otp given"}
        self.write(response)


class OtpAuthNewUserHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    users = MongoMixin.db.users
    otps = MongoMixin.db.otps

    @defer.inlineCallbacks
    def post(self):
        mob_num = self.request.arguments['mobile_number']
        """
        otp sms send
        """
        auth = yield self.users.find({"mobile_number": mob_num})
        if len(auth):
            """
            Mobile number exist
            """
            response = {"resp_code": False,
                        "data": "Mobile number already register"}
        else:
            """
            Mobile number does not exist
            """
            otp = randint(1000, 9999)
            timestamp = int(time.time())
            rs = yield self.otps.find({"mobile_numer": mob_num})
            if(len(rs) < 1):
                print("New OTP")
            else:
                print("Updating OTP")
                yield self.otps.remove({"mobile_numer": mob_num})
            yield self.otps.insert({"time": timestamp,
                                    "mobile_numer": mob_num,
                                    "otp": otp})
            log.msg("New registration:%r" % otp)
            mob_num = '91'+mob_num
            sms_resp = yield otpobj.send(mob_num, sender, otp)
            log.msg("sms_resp:%r" % sms_resp)
            response = {"resp_code": True}
        self.write(response)


#FName, LName, Mob, Role -> create u_id+token response
class OtpAuthValidateNewUserHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE", "PUT")
    users = MongoMixin.db.users
    otps = MongoMixin.db.otps
    devices = MongoMixin.db.devices
    entity = MongoMixin.db.entities

    """
    validating the user
    then adding to the user table
    sending token
    """
    @defer.inlineCallbacks
    def post(self):
        mob_num = self.request.arguments['mobile_number']
        otp_val = self.request.arguments['otp']
        rs = yield self.otps.find({"mobile_numer": mob_num})
        if not len(rs):
            response = {"resp_code": False, "data": "number not found"}
        else:
            if(int(otp_val) == rs[0]["otp"]):
                timestamp = int(time.time())
                role = self.request.arguments['role']
                email = self.request.arguments['email_id']
                full_name = self.request.arguments['full_name']
                user = self.request.arguments['username']
                rs = yield self.users.find({"mobile_number": mob_num})
                if len(rs):
                    log.msg("User already exist!!")
                    response = {"resp_code": False, "data": "Mobile number already exists"}
                else:
                    rsp = yield self.entity.find({"entity_name": "xlayer"})
                    if len(rsp):
                        ent_id = rsp[0]['_id']
                    else:
                        ent_id = "Not_assigned"
                    log.msg("New user entry!!")
                    yield self.users.insert({"create_time": timestamp,
                                             "mobile_number": mob_num,
                                             "role": role,
                                             "email_id": email,
                                             "full_name": full_name,
                                             "username": user,
                                             "password": "1234",
                                             "entity_id": ent_id,
                                             "l_latitude": "12.9152",
                                             "l_longitude": "77.6475",
                                             "l_update_time": timestamp})
                                             #ToDo: Currently hardcoded soon it willchange
                    auth = yield self.users.find({"mobile_number": mob_num})
                    if len(auth):
                        u_id = auth[0]["_id"]
                        self.token = get_token(u_id)
                        response = {'resp_code': True, 'token': self.token}
                        log.msg("Registration successful!!")
                    else:
                        log.msg("Mobile number is not valid")

                    if(role == "driver"):
                        log.msg("Role is driver")
                        imei = self.request.arguments['imei']
                        dev_type = self.request.arguments['dev_type']
                        yield self.users.find_and_modify(
                            query = {"mobile_number": mob_num},
                            update = {"$set": {"vehicles": []}}
                        )
                        yield self.devices.insert({"imei": imei,
                                                   "dev_type": dev_type,
                                                   "mobile_number": mob_num,
                                                   "status": "new",
                                                   "entity_id": ent_id})
                    elif(role == "admin"):
                        log.msg("Role is admin")
                    elif(role == "user"):
                        log.msg("role is user")
                        yield self.users.find_and_modify(
                            query = {"mobile_number": mob_num},
                            update = {"$set": {"vehicles": []}}
                        )
                    yield self.otps.remove({"mobile_numer": mob_num})
            else:
                log.msg("Registration! Wrong OTP entered.")
                response = {"resp_code": False, "data": "Wrong otp given"}
        self.write(response)

@jwtauth
class EmergencyMessageHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE", "PUT")
    users = MongoMixin.db.users
    vehicles = MongoMixin.db.vehicles
    alarms = MongoMixin.db.alarms
    get_data = GetKdbData()

    @defer.inlineCallbacks
    def post(self):
        notify_resp = False
        sms_resp = False
        v_id = self.request.arguments['v_id']
        try:
            u_id = self.request.arguments['u_id']
        except Exception, e:
            u_id = self.uid
        rlat = self.request.arguments['latitude']
        rlong = self.request.arguments['longitude']
        timestamp = self.request.arguments['timestamp']
        msg_type = self.request.arguments['type']
        data = self.request.arguments['message_data']
        log.msg("timestamp, msg_dt", timestamp, data)
        if(str(v_id) == ''):
            resp = {"resp_code": False, "data": "No vehicle present"}
        else:
            rsp = yield self.vehicles.find({"_id": ObjectId(v_id)})
            if len(rsp):
                reg_num = rsp[0]['reg_num']
                dr_num = rsp[0]['driver_number']
                es = yield self.users.find({"mobile_number": dr_num})
                if len(es):
                    log.msg('driver_name %r' % es[0]['full_name'])
                    driver_name = es[0]['full_name']
                else:
                    driver_name = "NA"
            else:
                reg_num = "NA"
                dr_num = "NA"
                driver_name = "NA"
            topic = "loc:"+v_id
            dt = yield self.get_data.kdb_get_data(topic, 0, 0)
            if(dt == 'NULL'):
                loc_resp = []
            else:
                loc_resp = dt
            if len(loc_resp):
                ulat = loc_resp[0]['latitude']
                ulong = loc_resp[0]['longitude']
            else:
                ulat = "NA"
                ulong = "NA"
            loc = [rlat, rlong]
            loc_addr = Nominatim()
            location = loc_addr.reverse(loc)
            addr = location.address
            temp = addr.split(',')
            temp = temp[:len(temp)-2]
            addr = ','.join(temp)
            """
            url = 'https://maps.googleapis.com/maps/api/geocode/json?latlng='rlat,rlong'&key=AIzaSyDseblqDtatfuby9akLweWn11pZ0GUgI88'
            gresp = yield cyclone.httpclient.fetch(url)
            """
            res = yield self.users.find({"_id": ObjectId(u_id)})
            if len(res):
                ent_id = res[0]['entity_id']
                mobile = res[0]['mobile_number']
                username = res[0]['full_name']
                rs = yield self.users.find({"role": "admin", "entity_id": ent_id})
                if len(rs):
                    admin_uid = str(rs[0]['_id'])
                    count = 0
                    es = yield self.alarms.find({"entity_id": ent_id, "alarm_type": data[0]['title']})
                    if len(es):
                        alm_id = es[0]['_id']
                        count = es[0]['count']
                        count = count + 1
                    yield self.alarms.find_and_modify(
                        query = {"_id": alm_id},
                        update = {"$set": {"count": count}}
                    )
                    mob_num = rs[0]['mobile_number']
                    #ToDo: title should be index use binary
                    pmessage = 'ALERT!!'+data[0]['title']+' vehicle '+reg_num+' user M:'
                    log.msg("Emergency SMS:%r" % pmessage)
                    panicobj = sendotp.sendotp(authkey, pmessage+' '+'{{otp}}.')
                    mob_num = '91'+mob_num
                    gresp = yield panicobj.send(mob_num, sender, int(mobile))
                    log.msg("panicresp:%r" % gresp)
                    sms_resp = True     #Need to handle the error
                    msg = {'type': msg_type,
                            'vehicle_id': v_id,
                            'username': username,
                            'driver_name': driver_name,
                            'reg_num': reg_num,
                            'user_number': mobile,
                            'driver_number': dr_num,
                            'timestamp': timestamp,
                            'address': addr,
                            'message_data': data}
                    #ToDo: send the admin uid
                    ret = user_send_msg(admin_uid, msg)
                    if ret == True:
                        rcode = True
                        rdata = "notification send succesfully",
                    else:
                        rcode = False
                        rdata = "notification not able to send",
                else:
                    rcode = False
                    rdata = "entity admin not found",
            else:
                rcode = False
                rdata = "requested user not found",

        resp = {'resp_code': rcode,
                'data': rdata,
                'sms': sms_resp,
                'notification': notify_resp}
        self.write(resp)
