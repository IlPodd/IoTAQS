from flask import Flask, jsonify, request, render_template, redirect, url_for
from flask_basicauth import BasicAuth

import math
import paho.mqtt.client as mqtt
import threading
import json

from pymongo import MongoClient


from utils.utils import send_mqtt_request, handle_sensor_message, handle_barrier_message,handle_broadcast_message,\
    create_s2_cell, decode_message

from parameters.Database_parameters import db_name, db_host, db_port
from parameters.Zone_JSON import geo_zones, geo_zones_json
from parameters.MQTT_parameters import MQTT_PORT, MQTT_BROKER, MQTT_TOPIC_ZONE, MQTT_REQUEST_BROADCAST, \
    MQTT_BARRIER_CONTROL, MQTT_ALL_TOPIC

from classes.CZone import Zone

from s2sphere import LatLng, Cell

"""-----DataBase-----"""
client = MongoClient(db_host, db_port)
db = client[db_name]
barriers_collection = db['barriers']
zone_collection = db['Zone']
devices_collection = db['devices']
sensors_collection = db['sensors']

"""-----MQTT----"""


# MQTT callback functions
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe(MQTT_ALL_TOPIC)


def on_message(client, userdata, msg):

    message_content = decode_message(msg)

    if message_content is None:
        return

    # Prevent a loop from response messages
    if message_content.startswith("RESPONSE:"):
        print(f"Response received -> {msg.topic}: {message_content}")
        return

    try:
        data = json.loads(message_content)
        #print(f"Parsed JSON data: {data}") #debugging

        if msg.topic.startswith(MQTT_BARRIER_CONTROL):
           # print('STARTING BARRIER HANDLE')
            handle_barrier_message(client, msg, data)
        elif msg.topic.startswith(MQTT_REQUEST_BROADCAST):
            handle_broadcast_message(client, msg,data)
        elif msg.topic.startswith(MQTT_TOPIC_ZONE):
           # print('STARTING Measurement HANDLE')

            handle_sensor_message(client, msg, data)
        else:
            raise Exception(f"Unhandled topic: {msg.topic}")

    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(f"Problematic message content: '{message_content}'")
    except KeyError as e:
        print(f"Missing key in JSON data: {e}")
    except Exception as e:
        print(f"Error processing message: {e}")


# MQTT client setup
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message


# Run MQTT client in a separate thread
def run_mqtt_client():
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()


mqtt_thread = threading.Thread(target=run_mqtt_client)
mqtt_thread.daemon = True
mqtt_thread.start()

"""/////////////////FLASK APIs//////////////////////////////"""
last_message = None
app = Flask(__name__)
messages = []
# Configure BasicAuth extension
app.config['BASIC_AUTH_USERNAME'] = 'admin'
app.config['BASIC_AUTH_PASSWORD'] = 'password'
basic_auth = BasicAuth(app)

"""----HOME PAGE-------"""


@app.route("/create_zone", methods=["POST"])
def create_zone():
    data = request.get_json()
    zone = Zone.create_zone(data["zone_id"], data["name"], data["barriers"], data["location"])
    return jsonify(zone.to_dict(), 201)


@app.route("/get_zones", methods=["GET"])
def get_zones():
    zones = Zone.get_zones()
    return jsonify([zone.to_dict() for zone in zones], 200)


@app.route('/home', methods=['GET'])
@app.route('/index', methods=['GET'])
@app.route('/', methods=['GET'])
def home():
    return render_template('home.html')




# Generate S2 cell data for the zones
s2_zones = []
for zone in geo_zones_json:
    lat, lng, _ = zone["p"]
    cell_id = create_s2_cell(lat, lng)
    cell = Cell(cell_id)
    vertices = []
    for i in range(4):
        vertex = cell.get_vertex(i)
        latlng = LatLng.from_point(vertex)
        vertices.append((latlng.lat().degrees, latlng.lng().degrees))
    s2_zones.append({"name": zone["n"], "vertices": vertices})

"""--------GET ZONE GEODATA PAGE------------"""


@app.route('/GetZones', methods=['GET'])
def send_zones():
    return geo_zones


"""----------------History Page"""


@app.route('/History', methods=['GET'])
def zone_history():
    # Get parameters from query string
    limit = request.args.get('limit', default=10, type=int)
    page = request.args.get('page', default=1, type=int)
    sort_field = request.args.get('sort_field', default='zone')
    sort_direction = request.args.get('sort_direction', default='asc')

    # Define limits for showing tables
    limit = max(1, min(limit, 100))  # Limit between 1 and 100
    total_entries = zone_collection.count_documents({})
    total_pages = max(1, math.ceil(total_entries / limit))
    page = max(1, min(page, total_pages))
    skips = limit * (page - 1)

    # Determine sort order
    sort_order = 1 if sort_direction == 'asc' else -1

    # Map sort_field to MongoDB field
    sort_field_map = {
        'zone': 'zone',
        'AQM': 'sensors.AQM',
        'time': 'time',
        'Temperature': 'sensors.Temperature',
        'Humidity': 'sensors.Humidity'
    }
    mongo_sort_field = sort_field_map.get(sort_field, 'zone')

    # Fetch data from MongoDB with skip, limit, and sort
    zones_cursor = zone_collection.find().sort(mongo_sort_field, sort_order).skip(skips).limit(limit)
    zones = list(zones_cursor)


    # Process data
    for zone in zones:
        try:
            # Convert ObjectId to string
            zone['_id'] = str(zone.get('_id', ''))

            # Handle 'zone' field
            zone['zone'] = zone.get('zone', 'N/A')

            # Handle 'sensors' field
            sensors = zone.get('sensors', {})
            zone['sensors'] = {
                'AQM': sensors.get('AQM', 'N/A'),
                'Temperature': sensors.get('Temperature', 'N/A'),
                'Humidity': sensors.get('Humidity', 'N/A')
            }

            # Handle 'time' field
            time_value = zone.get('time', 'N/A')
            if isinstance(time_value):
                # Format the datetime object
                formatted_time = time_value.strftime('%Y-%m-%d %H:%M:%S')
                zone['time'] = formatted_time
            else:
                zone['time'] = 'N/A'

        except Exception as e:
            print(f"Error processing zone data: {e}")
            continue  # Skip to the next document

    return render_template(
        'history.html',
        zones=zones,
        limit=limit,
        page=page,
        total_pages=total_pages,
        total_entries=total_entries,
        sort_field=sort_field,
        sort_direction=sort_direction
    )


@app.route('/Maps', methods=['GET'])
def visualize_zones():
    return render_template('Maps.html', s2_zones=s2_zones)


"""---------REAL TIME AIR QUALITY PAGE"""


# Route to render real-time data page
@app.route('/RealTime', methods=['GET'])
def real_time():
    # Placeholder for initial messages (replace with actual data received from MQTT)
    messages = ["Placeholder message 1", "Placeholder message 2"]
    return render_template('real_time_data.html', messages=messages)


# Route to handle request for new measurements via MQTT
@app.route('/request_measurement', methods=['POST'])
def request_measurement():
    send_mqtt_request()
    return jsonify({"status": "success"})


"""---------REAL TIME AIR QUALITY PAGE----"""

""" Control Panel Page"""

# Flask route to render control panel page

@app.route('/error_page')
def error_page():
    try:
        pass
    except Exception as e:
        error_message = f"An error occurred: {e}"
        return render_template('error.html', message=error_message)


@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == app.config['BASIC_AUTH_USERNAME'] and password == app.config['BASIC_AUTH_PASSWORD']:
            return redirect(url_for('control_panel'))
        else:
            return render_template('login.html', message="Invalid credentials. Please try again.")
    return render_template('login.html')

@app.route('/control_barrier', methods=['POST'])
def control_barrier():
    data = request.json
    barrier_id = data['barrier_id']
    action = data['action']

    # Publish MQTT message with the correct topic and payload
    topic = f"IoTAQStation/barriers/Parchetto_NE/{barrier_id}"
    payload = json.dumps({'command': action})

    client.publish(topic, payload)

    return jsonify({'status': 'success'})
@app.route('/control_panel', methods=['GET'])
@basic_auth.required
def control_panel():
    try:
        # Reading data from the barriers collection
        barriers_cursor = barriers_collection.find()
        barriers = list(barriers_cursor)

        # Aggregation pipeline to get the most recent entry per zone
        pipeline = [
            {
                '$sort': {'time': -1}  # Sort by 'time' in descending order
            },
            {
                '$group': {
                    '_id': '$zone',          # Group by 'zone'
                    'zone': {'$first': '$zone'},
                    'time': {'$first': '$time'},
                    'sensors': {'$first': '$sensors'},
                    'device_id': {'$first': '$device_id'}
                }
            }
        ]
        zones_cursor = zone_collection.aggregate(pipeline)
        zones = list(zones_cursor)

        # Render template with barriers and zones data
        return render_template('control_panel.html', barriers=barriers, zones=zones)

    except Exception as e:
        print(f"Error fetching data from MongoDB: {e}")
        return render_template('error.html', message="An error occurred while fetching data from the database.")


# Example usage
if __name__ == '__main__':
    app.run(debug=True)
