from enum import IntEnum
import paho.mqtt.publish as publish
import os, datetime
from dotenv import load_dotenv

from pathlib import Path  # python3 only
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

mqtt_server = os.getenv('MQTT_SERVER')
mqtt_port = int(os.getenv('MQTT_PORT'))

class Status(IntEnum):
    OFF = 0
    ON = 1

class SwitchDevice:
    def __init__(self, data, state):
        self.__status = state
        self.__lastHeartbeat = None
        self.deviceId = data.get('deviceId')
        self.pairingCode = data.get('pairingCode')
        self.type = data.get('type')
        self.manufacturerName = data.get('manufacturerName')
        self.friendlyName = data.get('friendlyName')
        self.description = data.get('description')
        self.alexa = data.get('alexa')


    def toEndpoint(self):
        endpoint = {
            "endpointId": self.deviceId,
            "manufacturerName": self.manufacturerName,
            "friendlyName": self.friendlyName,
            "description": self.description,
            "displayCategories": self.alexa.get('displayCategories'),
            "cookie": self.alexa.get('additionalDetails'),
            "capabilities": self.alexa.get('capabilities')
        }
        return endpoint

    def setStatus(self, status, broadcast=True):
        topic = None
        if status == Status.ON:
            topic = '{}/on'.format(self.deviceId)
        else:
            topic = '{}/off'.format(self.deviceId)
        if broadcast:
            publish.single(topic, hostname=mqtt_server, port=mqtt_port)
        self.__status = status
        return self.__status

    def updateHeartbeat(self):
        self.__lastHeartbeat = datetime.datetime.now()

    def isOnline(self, maxD=5.0):
        if not self.__lastHeartbeat: return False
        delta = datetime.datetime.now() - self.__lastHeartbeat
        return delta.seconds <= maxD

    def getStatus(self):
        return self.__status
