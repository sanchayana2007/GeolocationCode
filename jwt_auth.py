import jwt
import datetime
from twisted.python import log

SECRET = '12ksn639ej10dmeos0smct24dbdwievdwjwbvvfd1g2o'

options = {
    'verify_signature': True,
    'verify_exp': True,
    'verify_nbf': False,
    'verify_iat': True,
    'verify_aud': False
}

def get_token(u_id):
    encoded = jwt.encode({
        'sub': str(u_id),
        'a': {2: True},
        #Expire in one year = 31536000 sec
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7L)},
        SECRET,
        algorithm='HS256'
    )
    return encoded

def dec_token(token):
    try:
        dec_token = jwt.decode(token, SECRET, options=options)
        return dec_token['sub']
    except Exception, e:
        log.msg("Auth token decode failed, " + e.message)
        return False

def jwtauth(handler_class):
    ''' Handle Tornado JWT Auth '''
    def wrap_execute(handler_execute):
        def require_auth(handler, kwargs):
            auth = handler.request.headers.get('Authorization')
            if auth:
                parts = auth.split()
                if parts[0].lower() != 'bearer':
                    handler._transforms = []
                    handler.set_status(401)
                    handler.write("invalid header authorization")
                    handler.finish()
                elif len(parts) == 1:
                    handler._transforms = []
                    handler.set_status(401)
                    handler.write("invalid header authorization")
                    handler.finish()
                elif len(parts) > 2:
                    handler._transforms = []
                    handler.set_status(401)
                    handler.write("invalid header authorization")
                    handler.finish()

                token = parts[1]
                try:
                    dec_token = jwt.decode(token, SECRET, options=options)
                    handler.uid = dec_token['sub']
                except Exception, e:
                    handler._transforms = []
                    handler.set_status(401)
                    handler.write(e.message)
                    handler.finish()
            else:
                print("Auth unavailable");
                handler._transforms = []
                handler.set_status(501)
                handler.write("Missing authorization")
                handler.finish()

            return True

        def _execute(self, transforms, *args, **kwargs):

            try:
                require_auth(self, kwargs)
            except Exception:
                return False

            return handler_execute(self, transforms, *args, **kwargs)

        return _execute

    handler_class._execute = wrap_execute(handler_class._execute)
    return handler_class
