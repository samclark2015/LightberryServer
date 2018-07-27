import logging
from datetime import datetime

from flask import Flask
import json, re, os
import paho.mqtt.client as mqtt

from db import db
from routes.api import api

from authlib.flask.client import OAuth

mqtt_server = os.getenv('MQTT_SERVER')
mqtt_port = int(os.getenv('MQTT_PORT'))
secret = os.getenv('SECRET')

app = Flask(__name__)
oauth = OAuth(app)
app.secret_key = secret

# Logging setup
logger = logging.getLogger('lightberry_server')
logger.setLevel(logging.DEBUG)
# logging.basicConfig(format='%(asctime)s %(message)s', filename='/var/log/lightberry.log')

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

# store = loadData('data.pkl')

app.register_blueprint(api)

mqttc = mqtt.Client()


# MQTT Handlers & Connection
def getClientId(topic):
    regex = r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/.+'
    m = re.search(regex, topic)
    return m.group(1)


def handleStatusMessage(mosq, obj, msg):
    deviceId = getClientId(msg.topic)
    payload = msg.payload
    db.devices.update_one({'metadata.deviceId': deviceId}, {'$set': {'state': payload}})


def handleOnlineMessage(mosq, obj, msg):
    if msg.topic == 'host/online':
        return

    payload = json.loads(msg.payload)
    metadata = payload.get('metadata')

    logger.debug('Device {} online'.format(metadata.get('deviceId')))

    device = db.devices.find_one({'metadata.deviceId': metadata.get('deviceId')})
    if not device:
        payload['isLinked'] = False
        payload['lastHeartbeat'] = datetime.now()
        db.devices.insert(payload)


def handleHeartbeatMessage(mqttc, obj, msg):
    deviceId = getClientId(msg.topic)
    db.devices.update_one(
        {'metadata.deviceId': deviceId},
        {'$set': {'lastHeartbeat': datetime.now()}}
    )


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
    app.run(host='0.0.0.0', port=port, debug=True)
