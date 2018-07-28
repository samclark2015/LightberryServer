import json
import logging
import os
import re
from datetime import datetime

import paho.mqtt.client as mqtt

from db import db

mqttc = mqtt.Client()

logger = logging.getLogger('lightberry_server')
logger.setLevel(logging.DEBUG)

mqtt_server = os.getenv('MQTT_SERVER')
mqtt_port = int(os.getenv('MQTT_PORT'))


# MQTT Handlers & Connection
def getClientId(topic):
    regex = r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/.+'
    m = re.search(regex, topic)
    return m.group(1)


def handleStatusMessage(mosq, obj, msg):
    deviceId = getClientId(msg.topic)
    payload = msg.payload
    print(payload)
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
