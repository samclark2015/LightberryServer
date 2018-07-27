from logging import Handler


class MqttHandler(Handler):
    def __init__(self, mqttc, topic):
        super().__init__()
        self.mqttc = mqttc
        self.topic = topic

    def emit(self, record):
        log_entry = self.format(record)
        self.mqttc.publish(self.topic, log_entry)