import cyclone.web
from twisted.python import log
from web_utils import *
from common import *
import time
from jwt_auth import get_token

class UserTestHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ('GET', 'POST', 'PUT', 'DELETE')
    users = MongoMixin.db.users

    @defer.inlineCallbacks
    def post(self):
        us = 'user'
        i = 1
        lat = 12.4567
        longt = 77.6545
        v_id = ObjectId("5a9529ce3523897586a16f49")
        ent_id = ObjectId("5a9674a9352389465d0657c6")
        role = 'user'
        t = int(time.time())
        for j in range(1, 1000):
            mob_num = str(9001000000 + i)
            user = us+str(i)
            i = i + 1
            yield self.usr.insert({"role": role, "username": user, "mobile_number": mob_num,
                    "full_name": user, "vehicles": [v_id], "entity_id": ent_id, "password": "1234",
                    "email_id": user+'@gmail.com', "l_latitude": lat, "l_longitude": longt, "l_update_time": t})
            lat = lat + 0.002
            longt = longt + 0.001
        resp = {"resp_code": True, "data": "added successfully"}
        self.write(resp)

class TestTokenHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ('GET', 'POST', 'PUT', 'DELETE')
    users = MongoMixin.db.users

    @defer.inlineCallbacks
    def get(self):
        mob_num = self.get_arguments('mobile_number')
        mob_num = mob_num[0]
        password = "1234"
        auth = yield self.users.find({"mobile_number": mob_num, "password": password})
        if len(auth):
            log.msg("id is: %r" % auth[0]["_id"])
            u_id = auth[0]["_id"]
            self.token = get_token(u_id)
            response = {'resp_code': True, 'token': self.token}
            log.msg("Login successfully!")
        else:
            log.msg("Invalid username and password")
            response = {"resp_code": False, "data": "No data available"}
        self.write(response)


