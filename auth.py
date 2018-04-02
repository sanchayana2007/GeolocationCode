import cyclone.web
from twisted.python import log
from web_utils import *
from common import *
import jwt
import datetime
from jwt_auth import get_token

SECRET = 'my_secret_key'

class LoginHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    user = MongoMixin.db.users
    entity = MongoMixin.db.entities

    @defer.inlineCallbacks
    def get(self):
        username = self.get_arguments('username')
        username = username[0]
        password = self.get_arguments('password')
        password = password[0]
        auth = yield self.user.find({"username": username, "password": password})
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

    @defer.inlineCallbacks
    def post(self):
        mob_num = self.request.arguments['contact_number']
        password = self.request.arguments['password']
        auth = yield self.user.find({"mobile_number": mob_num, "password": password})
        if len(auth):
            if(auth[0]['role'] == "admin"):
                u_id = auth[0]["_id"]
                self.token = get_token(u_id)
                rs = yield self.user.find({"_id": u_id})
                if len(rs):
                    ent_id = rs[0]['entity_id']
                    res = yield self.entity.find({"_id": ent_id})
                    if len(res):
                        ent_name = res[0]["entity_name"]
                        if(ent_name == 'xlayer' or ent_name == "etrance"):
                            role = "super_admin"
                        else:
                            role = "admin"
                        response = {'resp_code': True, 'token': self.token, "role": role}
                        log.msg("Login successfully!")
                    else:
                        response = {"resp_code": False, "data": "No data available"}
                else:
                    response = {"resp_code": False, "data": "No data available"}
            else:
                response = {"resp_code": False, "data": "user is not admin"}
        else:
            log.msg("Invalid mobile_number and password")
            response = {"resp_code": False, "data": "No data available"}
        self.write(response)

