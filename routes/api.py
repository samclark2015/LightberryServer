import json
import os
from functools import wraps
from urllib.request import urlopen

from bson import json_util
from flask import Blueprint, request, jsonify
from jose import jwt

from db import db
from mqtt.client import mqttc
from utilities import toEndpoint

api = Blueprint('api', __name__, )

AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN')
API_AUDIENCE = os.getenv('AUTH0_AUDIENCE')
ALGORITHMS = ["RS256"]


class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


@api.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response


def get_token_auth_header():
    """Obtains the Access Token from the Authorization Header
    """
    auth = request.headers.get("Authorization", None)
    if not auth:
        raise AuthError({"code": "authorization_header_missing",
                         "description":
                             "Authorization header is expected"}, 401)

    parts = auth.split()

    if parts[0].lower() != "bearer":
        raise AuthError({"code": "invalid_header",
                         "description":
                             "Authorization header must start with"
                             " Bearer"}, 401)
    elif len(parts) == 1:
        raise AuthError({"code": "invalid_header",
                         "description": "Token not found"}, 401)
    elif len(parts) > 2:
        raise AuthError({"code": "invalid_header",
                         "description":
                             "Authorization header must be"
                             " Bearer token"}, 401)

    token = parts[1]
    return token


def requires_auth(f):
    """Determines if the Access Token is valid
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_auth_header()
        jsonurl = urlopen("https://{}/.well-known/jwks.json".format(AUTH0_DOMAIN))
        jwks = json.loads(jsonurl.read())
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
        if rsa_key:
            try:
                payload = jwt.decode(
                    token,
                    rsa_key,
                    algorithms=ALGORITHMS,
                    audience=API_AUDIENCE,
                    issuer="https://" + AUTH0_DOMAIN + "/"
                )

            except jwt.ExpiredSignatureError:
                raise AuthError({"code": "token_expired",
                                 "description": "token is expired"}, 401)
            except jwt.JWTClaimsError:
                raise AuthError({"code": "invalid_claims",
                                 "description":
                                     "incorrect claims,"
                                     "please check the audience and issuer"}, 401)
            except Exception:
                raise AuthError({"code": "invalid_header",
                                 "description":
                                     "Unable to parse authentication"
                                     " token."}, 401)

            user = db.users.find_one({'info.sub': payload.get('sub')})
            if not user:
                userRecord = {
                    'isAdmin': False,
                    'linkedDevices': [],
                    'info': payload
                }
                db.users.insert_one(userRecord)
            kwargs['user'] = payload
            return f(*args, **kwargs)
        raise AuthError({"code": "invalid_header",
                         "description": "Unable to find appropriate key"}, 401)

    return decorated


@api.route('/devices')
@requires_auth
def listDevices(user=None):
    user = db.users.find_one({'info.sub': user.get('sub')})
    deviceIds = user.get('linkedDevices')
    devices = db.devices.find({'metadata.deviceId': {'$in': deviceIds}})
    return json_util.dumps(devices)


@api.route('/devices/alexa')
@requires_auth
def listAlexaDevices(user=None):
    user = db.users.find_one({'info.sub': user.get('sub')})
    deviceIds = user.get('linkedDevices')
    devices = list(db.devices.find({'metadata.deviceId': {'$in': deviceIds}}))
    results = map(toEndpoint, devices)
    return json_util.dumps(results)


@api.route('/user')
@requires_auth
def getUser(user=None):
    user = db.users.find_one({'info.sub': user.get('sub')})
    return json_util.dumps(user)


@api.route('/devices/link', methods=['POST'])
@requires_auth
def linkDevice(user=None):
    content = request.json
    pairingCode = content.get('pairingCode')
    device = db.devices.find_one({'metadata.pairingCode': pairingCode})
    if not device:
        return jsonify(
            error='device not found'
        ), 404

    if device.get('isLinked'):
        return jsonify(
            error='device already linked'
        ), 405

    deviceId = device.get('metadata').get('deviceId')
    db.users.update_one(
        {'info.sub': user.get('sub')},
        {'$addToSet': {'linkedDevices': deviceId}}
    )
    db.devices.update_one({'metadata.deviceId': deviceId}, {'$set': {'isLinked': True}})
    return jsonify(
        status='device linked'
    )


@api.route('/devices/<deviceId>', methods=['GET', 'POST'])
@requires_auth
def device(deviceId, user=None):
    myDevices = db.users.find_one({'info.sub': user.get('sub')}).get('linkedDevices')
    if deviceId not in myDevices:
        raise AuthError({
            "code": "invalid_device",
            "description": "Device not linked!"
        }, 401)

    thisDevice = db.devices.find_one({'metadata.deviceId': deviceId})
    if request.method == 'GET':
        return jsonify(
            state=thisDevice.get('state')
        )
    else:
        content = request.values
        oldState = thisDevice.get('state')
        newState = content.get('state')
        # TODO: send MQTT message
        # mqttc.publish('{}/{}')
        return jsonify(
            previousState=oldState,
            state=newState
        )
