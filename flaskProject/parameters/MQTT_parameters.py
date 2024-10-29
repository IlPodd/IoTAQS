# MQTT Settings
KEEP_ALIVE = 60  # seconds

MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_TOPIC_BASE = 'IoTAQStation'
MQTT_TOPIC_ZONE = MQTT_TOPIC_BASE+'/zone'
MQTT_TOPIC_READINGS = MQTT_TOPIC_BASE+'/zone/+/devices/+/readings'  # Subscribe to all zones
MQTT_SENSORS = MQTT_TOPIC_BASE+'/devices/sensors'
MQTT_ALL_TOPIC = MQTT_TOPIC_BASE+'/#'
MQTT_ALL_DEVICES = MQTT_TOPIC_BASE+'/devices/#'
MQTT_REQUEST_BROADCAST= MQTT_TOPIC_BASE+'devices/+/readings/broadcast'
MQTT_BARRIER_CONTROL= MQTT_TOPIC_BASE+'/barriers'
MQTT_BARRIER_STATUS = MQTT_BARRIER_CONTROL+'/+/status'