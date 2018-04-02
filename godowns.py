import cyclone.web
import cyclone.httpclient
from twisted.python import log
from web_utils import *
from common import *


class GodownHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    godowns = MongoMixin.db.godowns

    @defer.inlineCallbacks
    def get(self):
        gd_id = self.get_arguments('gd_id')
        gd_id = gd_id[0]
        rs = yield self.godowns.find({"_id": ObjectId(gd_id)})
        if len(rs):
            for r in rs:
                v = {"gd_id": str(r['_id']), "godown_name": r['name'], "address": r['address'],
                        "contact_number": r['mobile_number'], "latitude": r['latitude'], "longitude": r['longitude']}
            resp = {"resp_code": True, "godown_data": v}
        else:
            resp = {"resp_code": False, "godown_data": "no data available"}
        self.write(resp)

    @defer.inlineCallbacks
    def post(self):
        name = self.request.arguments['name']
        address = self.request.arguments['address']
        mob_num = self.request.arguments['contact_number']
        lat = self.request.arguments['latitude']
        longt = self.request.arguments['longitude']
        rs = yield self.godowns.find({"name": name})
        if len(rs):
            resp = {"resp_code": False, "data": "godown already present"}
        else:
            yield self.godowns.insert({"name": name, "address": address, "mobile_number": mob_num,
                                        "latitude": lat, "longitude": longt})
            resp = {"resp_code": True, "data": "inserted successfully"}
        self.write(resp)

    @defer.inlineCallbacks
    def delete(self):
        gd_id = self.get_arguments('gd_id')
        gd_id = gd_id[0]
        rs = yield self.godowns.remove({"_id": ObjectId(gd_id)})
        if len(rs):
            resp = {"resp_code": True, "data": "deleted successfully"}
        else:
            resp = {"resp_code": False, "data": "delete failed"}
        self.write(resp)

    @defer.inlineCallbacks
    def put(self):
        gd_id = self.get_arguments('gd_id')
        gd_id = gd_id[0]
        name = self.request.arguments['name']
        address = self.request.arguments['address']
        mob_num = self.request.arguments['contact_number']
        lat = self.request.arguments['latitude']
        longt = self.request.arguments['longitude']
        rs = yield self.godowns.find_and_modify(
                query = {"_id": ObjectId(gd_id)},
                update = {"$set": {"name": name, "address": addr, "mobile_number": mob_num,
                                    "latitude": lat, "longitude": longt}}
            )
        if len(rs):
            resp = {"resp_code": True, "data": "updated_successfully"}
        else:
            resp = {"resp_code": False, "data": "update failed"}
        self.write(resp)

class CurrentGodownDetailsHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ('GET', 'POST', 'DELETE', 'PUT')
    godowns = MongoMixin.db.godowns

    @defer.inlineCallbacks
    def get(self):
        rs = yield self.godowns.find()
        result = []
        if len(rs):
            for r in rs:
                v = {"godown_id": str(r['_id']), "godown_name": r['name'], "address": r['address'],
                     "contact_number": r['mobile_number'], "latitude": r['latitude'], "longitude": r['longitude']}
                result.append(v)
            resp = {"resp_code": True, "godown_data": result}
        else:
            resp = {"resp_code": False, "godown_data": "No data available"}
        self.write(resp)
