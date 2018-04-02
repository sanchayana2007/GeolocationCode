import cyclone.web
from twisted.python import log
from web_utils import *
from common import *

class RouteHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    routes = MongoMixin.db.routes
    trips = MongoMixin.db.trips

    @defer.inlineCallbacks
    def get(self):
        r_id = self.get_arguments('r_id')
        r_id = r_id[0]
        rs = yield self.routes.find({"_id": ObjectId(r_id)})
        if len(rs):
            for r in rs:
                vendors = []
                for x in r['vendors']:
                    vendors.append(str(x))
                v = {"r_id": str(r['_id']), "start_location": r['start_location'], "vendor_list": vendors,
                     "end_location": r['end_location']}
            resp = {"resp_code": True, "route_data": v}
        else:
            resp = {"resp_code": False, "route_data": "no data available"}
        self.write(resp)

    @defer.inlineCallbacks
    def post(self):
        start = self.request.arguments['start_location']
        yield self.routes.insert({"start_location": start, "vendors": [], "end_location": start})
        self.write({"resp_code": True, "data": "inserted successfully"})

    @defer.inlineCallbacks
    def delete(self):
        r_id = self.get_arguments('r_id')
        r_id = r_id[0]
        rs = yield self.routes.remove({"_id": ObjectId(r_id)})
        yield self.trips.find_and_modify(
            query = {"route_id": ObjectId(r_id)},
            update = {"$set": {"route_id": "Not_assigned"}}
        )
        if len(rs):
            resp = {"resp_code": True, "data": "deleted successfully"}
        else:
            resp = {"resp_code": False, "data": "delete failed"}
        self.write(resp)

    @defer.inlineCallbacks
    def put(self):
        r_id = self.get_arguments('r_id')
        r_id = r_id[0]
        start = self.request.arguments['start_location']
        end = self.request.arguments['end_location']
        rs = yield self.routes.find_and_modify(
                query = {"_id": ObjectId(r_id)},
                update = {"$set": {"start_location": start, "end_location": end}}
            )
        if len(rs):
            resp = {"resp_code": True, "data": "updated successfully"}
        else:
            resp = {"resp_code": False, "data": "update failed"}
        self.write(resp)

class CurrentRouteDetailsHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ('GET', 'POST', 'DELETE', 'PUT')
    routes = MongoMixin.db.routes

    @defer.inlineCallbacks
    def get(self):
        rs = yield self.routes.find()
        result = []
        if len(rs):
            for r in rs:
                vendors = []
                for x in r['vendors']:
                    vendors.append(str(x))
                v = {"route_id": str(r['_id']), "start_location": r['start_location'], "vendors_list": vendors,
                     "end_location": r['end_location']}
                result.append(v)
            resp = {"resp_code": True, "route_data": result}
        else:
            resp = {"resp_code": False, "route_data": "no data available"}
        self.write(resp)

class AddVendorToRouteHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ('GET', 'POST', 'DELETE', 'PUT')
    routes = MongoMixin.db.routes

    @defer.inlineCallbacks
    def put(self):
        r_id = self.request.arguments['r_id']
        ven_id = self.request.arguments['ven_id']
        yield self.routes.find_and_modify(
            query = {"_id": ObjectId(r_id)},
            update = {"$push": {"vendors": ObjectId(ven_id)}}
        )
        self.write({"resp_code": True, "route_data": "assigned_successfully"})

    @defer.inlineCallbacks
    def delete(self):
        r_id = self.get_arguments('r_id')
        r_id = r_id[0]
        ven_id = self.get_arguments('ven_id')
        ven_id = ven_id[0]
        yield self.routes.find_and_modify(
            query = {"_id": ObjectId(r_id)},
            update = {"$pull": {"vendors": {"$in": [ObjectId(ven_id)]}}}
        )
        self.write({"resp_code": True, "trip_data": "deassigned_successfully"})

