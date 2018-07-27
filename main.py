import atexit, logging
from flask import Flask, jsonify, request
from functools import wraps
from appliances import Status, SwitchDevice
import json, re, os
import paho.mqtt.client as mqtt
from utilities import loadData, saveData, getUserFromToken
from frontend.dashboard import getDashboard
from authlib.flask.client import OAuth
from dotenv import load_dotenv

from pathlib import Path  # python3 only
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

mqtt_server = os.getenv('MQTT_SERVER')
mqtt_port = int(os.getenv('MQTT_PORT'))
secret = os.getenv('SECRET')

app = Flask(__name__)
oauth = OAuth(app)
app.secret_key = secret

# Logging setup
logging.basicConfig(format='%(asctime)s %(message)s', filename='/var/log/lightberry.log')

auth0 = oauth.register(
    'auth0',
    client_id=os.getenv('AUTH0_CLIENT_ID'),
    client_secret=os.getenv('AUTH0_CLIENT_SECRET'),
    api_base_url=os.getenv('AUTH0_API_BASE_URL'),
    access_token_url=os.getenv('AUTH0_ACCESS_TOKEN_URL'),
    authorize_url=os.getenv('AUTH0_AUTHORIZE_URL'),
    client_kwargs={
        'scope': 'openid profile',
    },
)

store = loadData('data.pkl')

app.register_blueprint(getDashboard(auth0, store))

mqttc = mqtt.Client()

def user_secret(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('AccessToken')
        if token in store.Users:
            kwargs['user'] = store.Users[token]
            return f(*args, **kwargs)
        else:
            userInfo = getUserFromToken(token)
            if userInfo:
                store.Users[token] = userInfo
                kwargs['user'] = userInfo
                return f(*args, **kwargs)
            else:
                return jsonify(error = 'unauthorized'), 401
    return decorated_function

def api_secret(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.headers.get('X-Secret') == secret:
            return f(*args, **kwargs)
        else:
            return jsonify(error = 'unauthorized'), 401
    return decorated_function

@app.route('/api/devices/')
@user_secret
def listDevices(user=None):
    myDevices = [x[1] for x in store.Links if x[0] == user.get('sub')]
    stats = {}
    for device in store.Devices:
        if device.deviceId in myDevices:
            stats[device.deviceId] = device.getStatus()
    return jsonify(stats)

@app.route('/api/devices/alexa')
@user_secret
def listAlexaDevices(user=None):
    myDevices = [x[1] for x in store.Links if x[0] == user.get('sub')]
    results = []
    for device in store.Devices:
        if device.deviceId in myDevices:
            results.append(device.toEndpoint())
    return jsonify(results)

@app.route('/api/devices/link', methods=['POST'])
@user_secret
def linkDevice(user=None):
    content = request.json
    pairingCode = content.get('pairingCode')
    user = content.get('user')
    devices = [x for x in store.Devices if x.pairingCode == pairingCode]
    if len(devices) < 1:
        return jsonify(
            error = 'device not found'
        ), 404
    device = devices[0]
    linkedDevices = [x for x in store.Links if x[1] == device.deviceId]
    if len(linkedDevices) != 0:
        return jsonify(
            error = 'device already linked'
        ), 405
    else:
        store.Links.append((user, device.deviceId))
        return jsonify(
            status = 'device linked'
        )

@app.route('/api/devices/<deviceId>', methods=['GET', 'POST'])
@user_secret
def device(deviceId, user=None):
    myDevices = [x[1] for x in store.Links if x[0] == user.get('sub')]
    if deviceId not in myDevices:
        return jsonify(
            error = 'unauthorized'
        ), 401

    devices = [x for x in store.Devices if x.deviceId == deviceId]
    if len(devices) < 1:
        return jsonify(
            error = 'device not found'
        ), 404
    device = devices[0]

    if request.method == 'GET':
        status = device.getStatus()
        return jsonify(
            status = status
        )
    else:
        content = request.values
        oldStatus = device.getStatus()
        status = int(content.get('status'))
        status = device.setStatus(Status(status))
        return jsonify(
            oldStatus = oldStatus,
            status = status
        )

# MQTT Handlers & Connection
def getClientId(topic):
    regex = r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/.+'
    m = re.search(regex, topic)
    return m.group(1)

def handleStatusMessage(mosq, obj, msg):
    id = getClientId(msg.topic)
    payload = json.loads(msg.payload)
    state = payload.get('state')
    device = store.getDevice(id)
    if device != None:
        device.setStatus(Status(state), broadcast=False)


def handleOnlineMessage(mosq, obj, msg):
    if msg.topic == 'host/online': return

    payload = json.loads(msg.payload)
    state = payload.get('state')
    metadata = payload.get('metadata')
    type = metadata.get('type')
    if type == 'switch':
        store.Devices.append(
            SwitchDevice(metadata, Status(state))
            )

def handleHeartbeatMessage(mqttc, obj, msg):
    id = getClientId(msg.topic)
    device = store.getDevice(id)
    if device != None:
        device.updateHeartbeat()

def handleConnect(mqttc, obj, flags, rc):
    mqttc.subscribe('+/status', 0)
    mqttc.subscribe('+/online', 0)
    mqttc.subscribe('+/heartbeat', 0)
    mqttc.publish('host/online')

def logMessage(mosq, obj, msg):
    logging.info('recieved message on %s', msg.topic)

mqttc.message_callback_add('*', logMessage)
mqttc.message_callback_add('+/status', handleStatusMessage)
mqttc.message_callback_add('+/online', handleOnlineMessage)
mqttc.message_callback_add('+/heartbeat', handleHeartbeatMessage)
mqttc.on_connect = handleConnect
mqttc.connect(mqtt_server, mqtt_port, 60)
mqttc.loop_start()

if __name__ == '__main__':
    port = os.getenv('HTTP_PORT', 1997)
    app.run(host='0.0.0.0',port=port, debug=True)

def onExit():
    saveData('data.pkl', store)

atexit.register(onExit)
