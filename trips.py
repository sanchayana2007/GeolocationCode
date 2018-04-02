import cyclone.web
from twisted.python import log
from web_utils import *
from common import *

class TripHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    trips = MongoMixin.db.trips

    @defer.inlineCallbacks
    def get(self):
        t_id = self.get_arguments('t_id')
        t_id = t_id[0]
        rs = yield self.trips.find({"_id": ObjectId(t_id)})
        if len(rs):
            for r in rs:
                v = {"t_id": str(r['_id']), "route_id": r['r_id'], "vehicle_id": r['v_id'],
                     "start_time": r['start_time'], "date": r['date']}
            resp = {"resp_code": True, "trip_data": v}
        else:
            resp = {"resp_code": False, "trip_data": "no date available"}
        self.write(resp)

    @defer.inlineCallbacks
    def post(self):
        start_time = self.request.arguments['start_time']
        date = self.request.arguments['date']
        rs = yield self.trips.insert({"r_id": "Not_assigned", "v_id": "Not_assigned",
                                     "start_time": start_time, "date": date})
        self.write({"resp_code": True, "data": "inserted successfully"})

    @defer.inlineCallbacks
    def delete(self):
        t_id = self.get_arguments('t_id')
        t_id = t_id[0]
        rs = yield self.trips.remove({"_id": ObjectId(t_id)})
        if len(rs):
            resp = {"resp_code": True, "data": "deleted successfully"}
        else:
            resp = {"resp_code": False, "data": "deletion failed"}
        self.write(resp)

    @defer.inlineCallbacks
    def put(self):
        t_id = self.get_arguments('t_id')
        t_id = t_id[0]
        start_time = self.request.arguments['start_time']
        date = self.request.arguments['date']
        rs = yield self.trips.find_and_modify(
                query = {"_id": ObjectId(t_id)},
                update = {"$set": {"start_time": start_time, "date": date}}
            )
        if len(rs):
            resp = {"resp_code": True, "data": "updated successfully"}
        else:
            resp = {"resp_code": False, "data": "update failed"}
        self.write(resp)

class CurrentTripDetailsHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ('GET', 'POST', 'DELETE', 'PUT')
    trips = MongoMixin.db.trips

    @defer.inlineCallbacks
    def get(self):
        rs = yield self.trips.find()
        result = []
        if len(rs):
            for r in rs:
                v = {"trip_id": str(r['_id']), "route_id": str(r['r_id']), "vehicle_id": str(r['v_id']),
                     "start_time": r['start_time'], "date": r['date']}
                result.append(v)
            resp = {"resp_code": True, "trip_data": result}
        else:
            resp = {"resp_code": False, "trip_data": "no data available"}
        self.write(resp)

class AddVehicleToTripHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ('GET', 'POST', 'DELETE', 'PUT')
    trips = MongoMixin.db.trips

    @defer.inlineCallbacks
    def put(self):
        t_id = self.request.arguments['trip_id']
        v_id = self.request.arguments['v_id']
        yield self.trips.find_and_modify(
            query = {"_id": ObjectId(t_id)},
            update = {"$set": {"v_id": ObjectId(v_id)}}
        )
        self.write({"resp_code": True, "trip_data": "assigned_successfully"})

    @defer.inlineCallbacks
    def delete(self):
        t_id = self.get_arguments('trip_id')
        t_id = t_id[0]
        v_id = self.get_arguments('v_id')
        v_id = v_id[0]
        yield self.trips.find_and_modify(
            query = {"_id": ObjectId(t_id)},
            update = {"$set": {"v_id": "Not_assigned"}}
        )
        self.write({"resp_code": True, "trip_data": "deassigned_successfully"})

class AddRouteToTripHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ('GET', 'POST', 'DELETE', 'PUT')
    trips = MongoMixin.db.trips

    @defer.inlineCallbacks
    def put(self):
        t_id = self.request.arguments['trip_id']
        r_id = self.request.arguments['r_id']
        yield self.trips.find_and_modify(
            query = {"_id": ObjectId(t_id)},
            update = {"$set": {"r_id": ObjectId(r_id)}}
        )
        self.write({"resp_code": True, "trip_data": "assigned_successfully"})

    @defer.inlineCallbacks
    def delete(self):
        t_id = self.get_arguments('trip_id')
        t_id = t_id[0]
        r_id = self.get_arguments('r_id')
        r_id = r_id[0]
        yield self.trips.find_and_modify(
            query = {"_id": ObjectId(t_id)},
            update = {"$set": {"r_id": "Not_assigned"}}
        )
        self.write({"resp_code": True, "trip_data": "deassigned_successfully"})

class AllTripDetailsHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ('GET', 'POST', 'DELETE', 'PUT')
    trips = MongoMixin.db.trips
    routes = MongoMixin.db.routes
    vendors = MongoMixin.db.vendors
    vehicles = MongoMixin.db.vehicles

    @defer.inlineCallbacks
    def get(self):
        rs = yield self.trips.find()
        result = []
        if len(rs):
            for r in rs:
                rt_id = r['r_id']
                if(rt_id == "Not_assigned"):
                    route = "NA"
                else:
                    res = yield self.routes.find({"_id": rt_id})
                    route = []
                    if len(res):
                        vendors = res[0]['vendors']
                        vendor = []
                        if len(vendors):
                            for ven_id in vendors:
                                resp = yield self.vendors.find({"_id": ven_id})
                                if len(resp):
                                    v = {"vendor_id": str(resp[0]['_id']), "vendor_name": resp[0]['name'],
                                        "vendor_address": resp[0]['address'],"latitude": resp[0]['latitude'],
                                        "longitude": resp[0]['longitude']}
                                    vendor.append(v)
                        v = {"route_id": str(res[0]['_id']), "start_location": res[0]['start_location'], "vendors": vendor,
                            "end_location": res[0]['end_location']}
                        route.append(v)
                v_id = r['v_id']
                if(v_id == "Not_assigned"):
                    vehicles = "NA"
                else:
                    resp = yield self.vehicles.find({"_id": v_id})
                    if len(resp):
                        vehicles = []
                        v = {"vehicle_id": str(resp[0]['_id']), "reg_num": resp[0]['reg_num'], "make": resp[0]['make'],
                            "model": resp[0]['model'], "color": resp[0]['colour'], "driver_number": resp[0]['driver_number']}
                        vehicles.append(v)
                v = {"trip_id": str(r['_id']), "route_data": route, "vehicle_data": vehicles, "start_time": r['start_time'],
                    "date": r['date']}
                result.append(v)
            resp = {"resp_code": True, "trip_data": result}
        else:
            resp = {"resp_code": True, "trip_data": "no data available"}
        self.write(resp)
