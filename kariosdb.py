import cyclone.web
import cyclone.httpclient
from twisted.python import log
from twisted.internet import reactor, task, defer
from twisted.internet.defer import returnValue
from web_utils import *
import time
import s2sphere
from s2sphere import CellId

class KariosDBConnection(object):
    def __init__(self, server='localhost', port='8080', ssl=False):
        self.ssl  = ssl
        self.server = server
        self.port = port
        self._generate_urls()

    def _generate_urls(self):
        if self.ssl is True:
            self.schema = "https"
        else:
            self.schema = "http"
        self.read_url     = "{0}://{1}:{2}/api/v1/datapoints/query".format(self.schema, self.server, self.port)
        self.read_tag_url = "{0}://{1}:{2}/api/v1/datapoints/query/tags".format(self.schema, self.server, self.port)
        self.write_url    = "{0}://{1}:{2}/api/v1/datapoints".format(self.schema, self.server, self.port)
        self.delete_dps_url = "{0}://{1}:{2}/api/v1/datapoints/delete".format(self.schema, self.server, self.port)
        self.delete_metric_url = "{0}://{1}:{2}/api/v1/metric/".format(self.schema, self.server, self.port)

    @staticmethod
    def handle_reply(r):
        log.msg("On handle response:%r" % r)

    @defer.inlineCallbacks
    def read(self, conn, metric_names, start_absolute=None, start_relative=None,
            end_absolute=None, end_relative=None, query_modifying_function=None,
            only_read_tags=False, tags=None):
        if start_relative is not None:
            query = self._query_relative(start_relative, end_relative)
        elif start_absolute is not None:
            start_time = float(start_absolute)   # This is here to confirm that the metric can be interpreted as a numeric
            query = {
                "start_absolute" : int(start_absolute * 1000)
            }
            if end_absolute is not None:
                end_time = float(end_absolute)
                query["end_absolute"] = int(end_absolute * 1000)

        if only_read_tags is True:
            read_url = conn.read_tag_url
        else:
            read_url = conn.read_url

        query["metrics"] = [ {"name" : m } for m in metric_names ]
        if tags:
            query['metrics'][0]['tags'] = tags

        log.msg("query items:%r" % query)

        r = yield cyclone.httpclient.fetch(read_url, postdata=json.dumps(query))

        r_dict = cyclone.escape.json_decode(r.body)
        defer.returnValue(r_dict)

    def write_one_metric(self, conn, name, timestamp, value, tags):
        if 'keys' not in dir(tags):
            raise TypeError, "The tags provided doesn't look enough like a dict: {0} is type {1}".format(tags, type(tags))
        metric = {
            "name" : name,
            "timestamp" : timestamp,
            "value" : value,
            "tags" : tags
        }
        return self.write_metrics_list(conn, [metric])

    @defer.inlineCallbacks
    def write_metrics_list(self, conn, metric_list):
        for m in metric_list:
            m["timestamp"] = int(m["timestamp"] * 1000)

        metrics = json.dumps(metric_list)
        g = yield cyclone.httpclient.fetch(conn.write_url, postdata=metrics)
        try:
            resp = cyclone.escape.json_decode(g.body)
        except ValueError:
            resp = {'success': 200}
        """
        Need to handle the response code
        """
        defer.returnValue(resp)

    def _query_relative(start, end=None):
        start_time = start[0] # This is here to confirm that the metric can be interpreted as a numeric
        start_unit = start[1]
        if start_unit not in VALID_UNITS:
            raise TypeError, "The time unit provided for the start time is not a valid unit: {0}".format(start)

        query = {
            "start_relative" : {"value": start_time, "unit": start_unit }
        }

        if end is not None:
            end_time = end[0]
            end_unit = end[1]
            if end_unit not in VALID_UNITS:
                raise TypeError, "The time unit provided for the end time is not a valid unit: {0}".format(end)
            query["end_relative"] = {"value" : end_time, "unit" : end_unit}

        return

    def read_absolute(self, conn, metric_names, start, end=None, tags=None,
                  query_modifying_function=None, only_read_tags=False):
        """If end_absolute is empty, time.time() is implied"""
        return self.read(conn, metric_names, start, end_absolute=end,
                    query_modifying_function=query_modifying_function,
                    only_read_tags=only_read_tags, tags=tags)


class GetKdbData(KariosDBConnection):
    ssl = False
    conn = KariosDBConnection('127.0.0.1', '8080', False)

    @defer.inlineCallbacks
    def kdb_get_data(self, topic, from_tm, to_tm):
        loc = []
        r = yield self.conn.read_absolute(self, [topic], from_tm, to_tm)
        log.msg("test_read_absolute_without_tags: ", r)
        length = r['queries'][0]['sample_size']
        if length:
            res = r['queries'][0]['results'][0]['values']
            for rs in res:
                val = CellId(rs[1])
                lat = val.to_lat_lng().lat().degrees
                longt = val.to_lat_lng().lng().degrees
                tm = rs[0] / 1000
                v = {"latitude": lat, "longitude": longt, "timestamp": tm}
                loc.append(v)
        returnValue(loc)

class TestKariosReadHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    entity = MongoMixin.db.entities
    users = MongoMixin.db.users
    get_data = GetKdbData()

    @defer.inlineCallbacks
    def post(self):
        log.msg("Got the TestKariosHandler req")
        from_tm = 0
        to_tm = 0
        #loc = []
        topic = "location"
        try:
            from_tm = self.request.arguments['start_time']
            to_tm = self.request.arguments['end_time']
        except Exception:
            log.msg("No time given, will give all location")
        if(from_tm != 0 and to_tm != 0):
            loc = self.get_data.kdb_get_data(topic, from_tm, to_tm)
        else:
            log.msg("inside else")
            r = yield self.conn.read_absolute(self, ["location"], 0)
            length = r['queries'][0]['sample_size']
            if length:
                if(length > 100):
                    n = 100
                else:
                    n = length
                res = r['queries'][0]['results'][0]['values']
                for i in range(0, n):
                    val = CellId(res[i][1])
                    lat = val.to_lat_lng().lat().degrees
                    longt = val.to_lat_lng().lng().degrees
                    tm = res[i][0] / 1000
                    v = {"latitude": lat, "longitude": longt, "timestamp": tm}
                    loc.append(v)
                data = loc
        self.write({"resp_code": True, "location": loc})

class TestKariosWriteHandler(JsonHandler, MongoMixin, KariosDBConnection):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    entity = MongoMixin.db.entities
    users = MongoMixin.db.users
    ssl = False
    conn = KariosDBConnection('127.0.0.1', '8080', ssl)

    @defer.inlineCallbacks
    def post(self):
        log.msg("Got the TestKariosWriteHandler req")
        lat = self.request.arguments['lat']
        longt = self.request.arguments['longt']
        t = int(time.time())
        pos = s2sphere.LatLng.from_degrees(float(lat), float(longt))
        s2cell = s2sphere.CellId.from_lat_lng(pos)
        val = s2cell.id()
        r = yield self.conn.write_one_metric(self, "location", t, val, tags = {"food_love" : "no"})
        self.write({"resp_code": True})
