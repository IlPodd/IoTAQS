# MQTT Settings
KEEP_ALIVE = 60  # seconds

MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883

# -------BASE TOPIC-------------

MQTT_TOPIC_BASE = 'IoTAQStation'
MQTT_ALL_TOPIC = MQTT_TOPIC_BASE + '/#'
MQTT_RESPONSE_TOPIC = "IoTAQStation/responses"

# -------ZONE TOPICS-------------

MQTT_TOPIC_ZONE = MQTT_TOPIC_BASE + '/zone'

# -------SENSORS TOPICS-------------

MQTT_TOPIC_READINGS = MQTT_TOPIC_BASE + '/zone/+/devices/+/readings'  # Subscribe to all devices readings
MQTT_SENSORS = MQTT_TOPIC_BASE + '/devices/sensors'
MQTT_ALL_DEVICES = MQTT_TOPIC_BASE + '/devices/#'
MQTT_REQUEST_BROADCAST = MQTT_ALL_DEVICES

# -------BARRIER TOPICS-------------
MQTT_BARRIER_CONTROL = MQTT_TOPIC_BASE + '/barriers'
MQTT_BARRIER_STATUS = MQTT_BARRIER_CONTROL + '/+/status'
