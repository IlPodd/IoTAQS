from parameters.MQTT_parameters import MQTT_REQUEST_BROADCAST
import json
import paho.mqtt.client as mqtt
from datetime import datetime
from pymongo import MongoClient
from s2sphere import LatLng, CellId, Cell
import uuid
from bson import Binary

client = mqtt.Client()
db_client = MongoClient('localhost', 27017)
db = db_client['SmartStation']
barriers_collection = db['barriers']
zone_collection = db['Zone']
devices_collection = db['devices']
sensors_collection = db['sensors']
requests_collection = db['requests']

def decode_message(msg):
    try:
        message_content = msg.payload.decode('utf-8')
        print(f"Decoded message content: '{message_content}'")
        return message_content
    except UnicodeDecodeError as e:
        print(f"Unicode decode error: {e}")
        return None


def handle_barrier_message(client, msg, data):
    topic_parts = msg.topic.split('/')
    # Topic structure: IoTAQStation/Zones/{zone_name}}/Barriers/{barrier_id}
    barrier_id = topic_parts[4]  # Extract 'barrier_id'
    zone = topic_parts[2]        # Extract 'zone_name' if needed

    # Verify the message type and id_req
    if data.get("type") == "status" and "id_req" in data:
        action = data.get("data")  # 'open' or 'close'
        id_req_str = data.get("id_req")

        try:
            # Look up the original request in MongoDB
            result = requests_collection.find_one({'id_request': id_req_str})

            if result:
                # Update barrier status in MongoDB
                barriers_collection.update_one(
                    {'barrier_id': barrier_id},
                    {'$set': {'status': action == 'open'}}
                )
                print(f"Barrier {barrier_id} status updated to {action}")

                # Update the request status to 'completed'
                requests_collection.update_one(
                    {'id_request': id_req_str},
                    {'$set': {
                        'status': 'completed',
                        'outcome': 'success',
                        'response_time': datetime.now()
                    }}
                )

                # Optionally publish a response message or perform additional actions

            else:
                print(f"No matching request found for id_req {id_req_str}.")

        except Exception as e:
            # Handle exceptions and update request outcome
            requests_collection.update_one(
                {'id_request': id_req_str},
                {'$set': {'outcome': 'failed'}}
            )
            print(f"Error handling barrier status update: {e}")
    else:
        print("Unrecognized barrier message format or missing id_req")


def create_s2_cell(lat, lng, level=19):
    latlng = LatLng.from_degrees(lat, lng)
    cell_id = CellId.from_lat_lng(latlng).parent(level)
    return cell_id


def handle_sensor_message(client, msg, data):
    if data.get('type') == 'status':
        print("Received barrier status message in handle_sensor_message, ignoring.")
        return
    topic_parts = msg.topic.split('/')
    zone = topic_parts[1]  # Extract zone from the topic

    # Extract sensor data
    latitude = data.get('Latitude')
    longitude = data.get('Longitude')
    temperature = data.get('Temperature')
    zone = data.get('Zone')
    humidity = data.get('Humidity')
    aqm = data.get('AQM')

    sensors_data = {
        'Temperature': temperature,
        'Humidity': humidity,
        'AQM': aqm
    }

    message_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    insert_data = {
        'latitude': latitude,
        'longitude': longitude,
        'zone': zone,
        'sensors': sensors_data,
        'time': message_time
    }

    try:
        result = zone_collection.insert_one(insert_data)
        print(f"Data inserted into MongoDB with object ID: {result.inserted_id}")
    except Exception as e:
        print(f'Error while inserting data into database: {e}')

    # Publish a response
    response_message = "RESPONSE: DATA STORED"
    client.publish(msg.topic, response_message)
    print(f"Response published to {msg.topic}")


def handle_broadcast_message(client, msg, data):
    return handle_sensor_message(client, msg, data)


def send_mqtt_request(request_data):
    client.publish(MQTT_REQUEST_BROADCAST, json.dumps(request_data), qos=1)
    print(f"Sent request: {json.dumps(request_data)}")


def send_barrier_command(client, barrier_id, action, pending_commands):
    topic = f"IoTAQStation/BARRIERS/{barrier_id}/COMMAND"
    client.publish(topic, action)
    pending_commands[barrier_id] = {'action': action, 'time': datetime.utcnow()}
    print(f"Command '{action}' sent to barrier {barrier_id}")





def transform_geo_zone(geo_zones_json):
    # Iterate through each item in geo_zones_json and reformat it
    transformed = [
        [item["p"][0], item["p"][1], item["p"][2], item["n"]]
        for item in geo_zones_json
    ]

    # Convert the transformed list to a JSON-style string
    geo_zones = json.dumps(transformed)

    return geo_zones