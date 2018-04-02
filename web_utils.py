import cyclone.web
import json
import tornado.web
import txmongo
import txmongo.filter
from twisted.enterprise import adbapi
from bson import json_util
from bson.objectid import ObjectId

class MongoMixin(object):
    mongo_host = "127.0.0.1"
    mongo_port = 27017
    dbpool = txmongo.MongoConnection(mongo_host, mongo_port)
    db = dbpool.gpsdb

class BaseHandler(cyclone.web.RequestHandler):
    def get_current_user(self):
        user_json = self.get_secure_cookie("user")
        print("get_current_user", user_json)
        if not user_json:
            return None
        return cyclone.escape.json_decode(user_json)

    def get_current_device(self):
        device_json = self.get_secure_cookie("imei")
        print("get_current_device", device_json)
        if not device_json:
            return None
        return cyclone.escape.json_decode(device_json)

class JsonHandler(BaseHandler):
    """Request handler where requests and responses speak JSON."""
    def prepare(self):
        # Incorporate request JSON into arguments dictionary.
        if self.request.body:
            try:
                json_data = json.loads(self.request.body)
                self.request.arguments.update(json_data)
            except ValueError:
                message = 'Unable to parse JSON.'
                self.send_error(400, message=message) # Bad Request

        # Set up response dictionary.
        self.response = dict()

    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json')

    def write_error(self, status_code, **kwargs):
        if 'message' not in kwargs:
            if status_code == 405:
                kwargs['message'] = 'Invalid HTTP method.'
            else:
                kwargs['message'] = 'Unknown error.'

        self.response = kwargs
        self.write_json()

    def write_json(self):
        output = json.dumps(self.response)
        self.write(output)
