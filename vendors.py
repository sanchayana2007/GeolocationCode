import cyclone.web
from twisted.python import log
from web_utils import *
from common import *


class VendorHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    vendors = MongoMixin.db.vendors

    @defer.inlineCallbacks
    def get(self):
        ven_id = self.get_arguments('ven_id')
        ven_id = ven_id[0]
        rs = yield self.vendors.find({"_id": ObjectId(ven_id)})
        if len(rs):
            for r in rs:
                v = {"vendor_id": str(r['_id']), "vendor_name": r['name'], "address": r['address'],
                     "contact_number": r['mobile_number'], "latitude": r['latitude'], "longitude": r['longitude']}
            resp = {"resp_code": True, "vendor_data": v}
        else:
            resp = {"resp_code": False, "vendor_data": "no data available"}
        self.write(resp)

    @defer.inlineCallbacks
    def post(self):
        name = self.request.arguments['name']
        addr = self.request.arguments['address']
        mob_num = self.request.arguments['contact_number']
        lat = self.request.arguments['latitude']
        longt = self.request.arguments['longitude']
        rs = yield self.vendors.find({"name": name})
        if len(rs):
            resp = {"resp_code": True, "data": "vendor already present"}
        else:
            yield self.vendors.insert({"name": name, "address": addr, "mobile_number": mob_num,
                                        "latitude": lat, "longitude": longt})
            resp = {"resp_code": True, "data": "inserted successfully"}
        self.write(resp)

    @defer.inlineCallbacks
    def delete(self):
        ven_id = self.get_arguments('ven_id')
        ven_id = ven_id[0]
        rs = yield self.vendors.remove({"_id": ObjectId(ven_id)})
        if len(rs):
            resp = {"resp_code": True, "data": "deleted successfully"}
        else:
            resp = {"resp_code": False, "data": "delete failed"}
        self.write(resp)

    @defer.inlineCallbacks
    def put(self):
        ven_id = self.get_arguments('ven_id')
        ven_id = ven_id[0]
        name = self.request.arguments['name']
        addr = self.request.arguments['address']
        contact_num = self.request.arguments['contact_number']
        lat = self.request.arguments['latitude']
        longt = self.request.arguments['longitude']
        rs = yield self.vendors.find_and_modify(
                query = {"_id": ObjectId(ven_id)},
                update = {"$set": {"name": name, "address": addr, "mobile_number": contact_num,
                                    "latitude": lat, "longitude": longt}}
            )
        if len(rs):
            resp = {"resp_code": True, "data": "updated successfully"}
        else:
            resp = {"resp_code": False, "data": "update failed"}
        self.write(resp)

class CurrentVendorDetailsHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ('GET', 'POST', 'DELETE', 'PUT')
    vendors = MongoMixin.db.vendors

    @defer.inlineCallbacks
    def get(self):
        rs = yield self.vendors.find()
        result = []
        if len(rs):
            for r in rs:
                v = {"vendor_id": str(r['_id']), "vendor_name": r['name'], "address": r['address'],
                     "contact_number": r['mobile_number'], "latitude": r['latitude'], "longitude": r['longitude']}
                result.append(v)
            resp = {"resp_code": True, "vendor_data": result}
        else:
            resp = {"resp_code": False, "vendor_data": "No data available"}
        self.write(resp)
