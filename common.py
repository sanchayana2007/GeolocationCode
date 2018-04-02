import functools
import cyclone.web
from twisted.internet import defer

def dbsafe(method):
    @defer.inlineCallbacks
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            result = yield defer.maybeDeferred(method, self, *args, **kwargs)
            '''
        except MySQLdb.OperationalError, e:
            log.msg("MySQL error: " + str(e))
            '''
        except cyclone.redis.RedisError, e:
            log.msg("Redis error: " + str(e))
        else:
            defer.returnValue(result)
        raise web.HTTPError(503)  # Service Unavailable
    return wrapper

