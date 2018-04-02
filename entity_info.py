import cyclone.web
from twisted.python import log
from web_utils import *
from common import *
from jwt_auth import jwtauth

server_url = "https://live.trakiga.com"

@jwtauth
class EntityInfoHandler(JsonHandler, MongoMixin):
    SUPPORTED_METHODS = ("GET", "POST", "DELETE","PUT")
    entity = MongoMixin.db.entities
    users = MongoMixin.db.users

    @defer.inlineCallbacks
    def get(self):
            u_id = self.uid
            rs = yield self.users.find({"_id": ObjectId(u_id)})
            if len(rs):
                entity_id = rs[0]["entity_id"]
                es = yield self.entity.find({"_id": entity_id})
                ent_data = []
                if len(es):
                    log.msg("entity data avilable")
                    v = {'entity_id': str(es[0]['_id']),
                         'entity_name': es[0]["entity_name"],
                         'owner_name': es[0]["owner"],
                         'mobile_number': es[0]["mobile_number"],
                         'emergency_number': es[0]["emergency_mobile_number"],
                         'email_id': es[0]['email_id'],
                         'alternate_email': es[0]['alternate_email_id'],
                         'entity_address': es[0]['address'],
                         'entity_logo': server_url+"/uploads/"+str(es[0]['_id'])+"/"+str(es[0]['_id'])+".png"   #es[0]['entity_logo']
                    }
                    ent_data.append(v)
                    resp = {"resp_code": True, "entity_data": ent_data}
		else:
                    """
                    ToDo: Deafualt entity details need to send
                    """
                    log.msg("entity not avilable")
                    v = {'entity_id': "Default",
                         'entity_name':"xLayer Technologies",
                         'owner_name':"xlayer",
                         'mobile_number': "9584956125",
                         'emergency_number': "8085461683",
                         'email_id': 'xlayertechnologies.in',
                         'alternate_email': 'subrata.debnath@gmail.com',
                         'entity_address': 'btm 2nd tage',
                         'entity_logo': "http://tracker.xlayer.in"   #es[0]['entity_logo']
                    }
                    ent_data.append(v)
                    resp = {"resp_code": False, "entity_data": ent_data}
            else:
                log.msg("user not avilable")
                resp = {'resp_code': False, 'user_data': "user data not available"}
            self.write(resp)

