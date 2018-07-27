import os
from functools import wraps
from flask import Blueprint, request, jsonify
from db import db
from utilities import getUserFromToken, toEndpoint

api = Blueprint('api', __name__, )
secret = os.getenv('SECRET')


def user_secret(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('AccessToken')
        user = db.users.find_one({'token': token})
        if user:
            kwargs['user'] = user.get('info')
            return f(*args, **kwargs)
        else:
            userInfo = getUserFromToken(token)
            if userInfo:
                user = db.users.find_one({'info.sub': userInfo.get('sub')})
                if user:
                    db.users.update_one({'info.sub': userInfo.get('sub')}, {'$set': {'token': token}})
                else:
                    userRecord = {
                        'token': token,
                        'linkedDevices': [],
                        'info': userInfo
                    }
                    db.users.insert(userRecord)
                kwargs['user'] = userInfo
                return f(*args, **kwargs)
            else:
                return jsonify(error='unauthorized'), 401

    return decorated_function


def api_secret(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.headers.get('X-Secret') == secret:
            return f(*args, **kwargs)
        else:
            return jsonify(error='unauthorized'), 401

    return decorated_function


@api.route('/api/devices/')
@user_secret
def listDevices(user=None):
    user = db.users.find_one({'info.sub': user.get('sub')})
    deviceIds = user.get('linkedDevices')
    devices = db.devices.find({'metdata.deviceId': {'$in': deviceIds}})
    return jsonify(devices)


@api.route('/api/devices/alexa')
@user_secret
def listAlexaDevices(user=None):
    user = db.users.find_one({'info.sub': user.get('sub')})
    deviceIds = user.get('linkedDevices')
    devices = db.devices.find({'metdata.deviceId': {'$in': deviceIds}})
    results = map(toEndpoint, devices)
    return jsonify(results)


@api.route('/api/devices/link', methods=['POST'])
@user_secret
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
    db.devices.update_one({'metadata.deviceId': device}, {'$set': {'isLinked': True}})
    return jsonify(
        status='device linked'
    )


'''
@api.route('/api/devices/<deviceId>', methods=['GET'])
@user_secret
def device(deviceId, user=None):
    myDevices = [x[1] for x in store.Links if x[0] == user.get('sub')]
    if deviceId not in myDevices:
        return jsonify(
            error='unauthorized'
        ), 401

    devices = [x for x in store.Devices if x.deviceId == deviceId]
    if len(devices) < 1:
        return jsonify(
            error='device not found'
        ), 404
    device = devices[0]

    if request.method == 'GET':
        status = device.getStatus()
        return jsonify(
            status=status
        )
    else:
        content = request.values
        oldStatus = device.getStatus()
        status = int(content.get('status'))
        status = device.setStatus(Status(status))
        return jsonify(
            oldStatus=oldStatus,
            status=status
        )
'''
