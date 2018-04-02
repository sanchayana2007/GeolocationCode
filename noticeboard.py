import cyclone.web
from twisted.python import log
from web_utils import *
from common import *
from jwt_auth import jwtauth

@jwtauth
class NoticeBoardHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    notices = MongoMixin.db.notices
    entity = MongoMixin.db.entity
    users = MongoMixin.db.users

    @defer.inlineCallbacks
    def post(self):
        rs = yield self.users.find({"_id": ObjectId(self.uid)})
        if len(rs):
            print("Getting msg from db", rs[0]["role"])
            if str(rs[0]["role"]) == "admin":
                content = self.request.arguments
                log.msg("content: %r" % content)
                ent_id = rs[0]['entity_id']
                yield self.notices.insert({"admin_id": ObjectId(self.uid), "entity_id": ent_id, "notice": content})
                data = "notice inserted"
		rcode = True
                es = yield self.users.find({"entity_id": ent_id})
            else:
                print("user is not admin")
                rcode = False
                data = "user is not admin"
        else:
            print("else function calling")
            data = "invalid user"
	    rcode = False
        resp = {"resp_code": rcode, "data": data}
        self.write(resp)


    @defer.inlineCallbacks
    def get(self):
        log.msg("data available")
        rs = yield self.users.find({"_id": ObjectId(self.uid)})
        result = []
        if len(rs):
            ent_id = rs[0]['entity_id']
            dt = yield self.notices.find({"entity_id": ObjectId(ent_id)})
            if len(dt):
                for d in dt:
                    log.msg("data available")
                    v = {"notice_id": str(d['_id']), "notice_data": dt[0]['notice']}
                    result.append(v)
                data = result
                rcode = True
            else:
                log.msg("data not available")
                data = 'NULL'
                rcode = False
        else:
            rcode = False
            data = "User not found"
        resp = {"resp_code": rcode, "data": data}
        self.write(resp)

    @defer.inlineCallbacks
    def delete(self):
        n_id = self.get_arguments('notice_id')
        n_id = n_id[0]
        rs = yield self.users.find({"_id": ObjectId(self.uid)})
        if len(rs):
            print("Getting msg from db", rs[0]["role"])
            if str(rs[0]["role"]) == "admin":
                rs = yield self.notices.find({"_id": ObjectId(n_id)})
                if len(rs):
                    yield self.notices.remove({"_id": ObjectId(n_id)})
                    rcode = True
                    data = "deleted successfully"
                else:
                    rcode = False
                    data = "NULL"
            else:
                rcode = False
                data = "user is not admin"
        else:
            rcode = False
            data = "Invalid notice id"
        resp = {"resp_code": rcode, "data": data}
        self.write(resp)

    @defer.inlineCallbacks
    def put(self):
        rs = yield self.users.find({"_id": ObjectId(self.uid)})
        if len(rs):
            print("Getting msg from db", rs[0]["role"])
            if str(rs[0]["role"]) == "admin":
                notice_id = self.request.arguments['notice_id']
                content = self.request.arguments['data']
                log.msg("content: %r" % content)
                rs = yield self.notices.find_and_modify(
                    query = {"_id": ObjectId(notice_id)},
                    update = {"$set": {"notice": content}}
                )
                rcode = True
                data = "updated successfully"
            else:
                rcode = False
                data = "user not admin"
        else:
            rcode = False
            data = "invalid user"
        resp = {"resp_code": rcode, "data": data}
        self.write(resp)

class ImageUploadFileHandler(cyclone.web.RequestHandler):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")

    def post(self):
        fileinfo = self.request.files['file'][0]
        fname = fileinfo['filename']
        filepath = '/home/'+getpass.getuser()+'/tracker/'
        fh = open(filepath+fname, 'w')
        fh.write(fileinfo['body'])
        fh.close()
        self.write({'result': True, 'filepath': filepath})















