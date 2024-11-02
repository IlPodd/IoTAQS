from flask import Flask, jsonify, request, render_template, redirect, url_for
from flask_basicauth import BasicAuth
from bson import json_util
import math
import paho.mqtt.client as mqtt
import threading
import json
from datetime import datetime
import uuid

from pymongo import MongoClient

from utils.utils import handle_sensor_message, handle_barrier_message, decode_message, transform_geo_zone

from parameters.Database_parameters import db_name, db_host, db_port
from parameters.Zone_JSON import geo_zones
from parameters.MQTT_parameters import *

from classes.CZone import Zone
from classes.CRequests import Request
from classes.CBarrier import Barrier

"""-----DataBase-----"""
client = MongoClient(db_host, db_port)
db = client[db_name]
barriers_collection = db['barriers']
zone_collection = db['Zone']
requests_collection = db["requests"]

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
        #print(f"Response received -> {msg.topic}: {message_content}") #for debugging
        return

    try:
        data = json.loads(message_content)
        message_type = data.get('type')

        if message_type == 'status':
            print('STARTING BARRIER STATUS HANDLE')
            handle_barrier_message(client, msg, data)
        elif message_type == 'command':
            pass  # command should not be received by the server
        elif message_type == 'measurement':
            print('STARTING MEASUREMENT HANDLE')
            handle_sensor_message(client, msg, data)
        else:
            print(f"Unhandled message type: {message_type}")

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
# Configure BasicAuth
app.config['BASIC_AUTH_USERNAME'] = 'admin'
app.config['BASIC_AUTH_PASSWORD'] = 'password'
basic_auth = BasicAuth(app)

"""----HOME PAGE-------"""


@app.route("/create_zone", methods=["POST"])
def create_zone():
    data = request.get_json()
    zone = Zone.create_zone(data["zone_id"], data["name"], data["barriers"], data["location"])
    return jsonify(zone.to_dict(), 201)


@app.route('/home', methods=['GET'])
@app.route('/index', methods=['GET'])
@app.route('/', methods=['GET'])
def home():
    return render_template('home.html')


"""--------GET ZONE GEODATA PAGE------------"""


@app.route('/GetZones', methods=['GET'])
def send_zones():
    return geo_zones

"""----------------History Page-------"""


@app.route('/History', methods=['GET'])
def zone_history():
    # Get parameters from query string
    limit = request.args.get('limit', default=10, type=int)
    page = request.args.get('page', default=1, type=int)
    sort_field = request.args.get('sort_field', default='zone')
    sort_direction = request.args.get('sort_direction', default='asc')

    # Define limits for the tables
    limit = max(1, min(limit, 100))
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

            # Use 'time' field as-is
            zone['time'] = zone.get('time', 'N/A')

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


@app.route('/History/download', methods=['GET'])
def download_zone_history():
    try:
        # Fetch all historical data, with optional sorting and pagination logic if required
        zones_cursor = zone_collection.find().sort("time", -1)
        zones = list(zones_cursor)

        # Process data
        for zone in zones:
            zone['_id'] = str(zone.get('_id', ''))
            zone['zone'] = zone.get('zone', 'N/A')
            sensors = zone.get('sensors', {})
            zone['sensors'] = {
                'AQM': sensors.get('AQM', 'N/A'),
                'Temperature': sensors.get('Temperature', 'N/A'),
                'Humidity': sensors.get('Humidity', 'N/A')
            }
            time_value = zone.get('time', 'N/A')
            if isinstance(time_value, datetime):
                zone['time'] = time_value.strftime('%Y-%m-%d %H:%M:%S')
            else:
                zone['time'] = 'N/A'

        # Send data in JSON format
        return jsonify(zones)

    except Exception as e:
        print(f"Error fetching history data for download: {e}")
        return jsonify({"error": "An error occurred while fetching data"}), 500


"""------------MAP  WITH ZONES PAGE --------"""


@app.route('/Maps', methods=['GET'])
def visualize_zones():
    return render_template('Maps.html')


"""---------REAL TIME AIR QUALITY PAGE"""


@app.route('/RealTime', methods=['GET'])
def real_time():
    sort_field = request.args.get('sort_field', 'zone')
    sort_order = int(request.args.get('sort_order', 1))  # 1 for ascending, -1 for descending

    # Field mapping for MongoDB
    field_map = {
        'zone': 'zone',
        'AQM': 'sensors.AQM',
        'Temperature': 'sensors.Temperature',
        'Humidity': 'sensors.Humidity',
        'status': 'status',
        'time': 'time'
    }
    # Map to MongoDB field
    sort_field_mongo = field_map.get(sort_field, 'zone')

    try:
        # Aggregation pipeline to get the latest entry per zone
        pipeline = [
            {'$sort': {'time': -1}},  # Sort by 'time' descending
            {
                '$group': {
                    '_id': '$zone',
                    'zone': {'$first': '$zone'},
                    'time': {'$first': '$time'},
                    'sensors': {'$first': '$sensors'},
                    'DEVICE_ID': {'$first': '$DEVICE_ID'}
                }
            }
        ]
        zones_cursor = zone_collection.aggregate(pipeline)
        zones = list(zones_cursor)

        # Fetch statuses from 'barriers' collection and create a mapping
        barriers_cursor = barriers_collection.find({}, {'zone': 1, 'status': 1})
        status_map = {barrier['zone']: barrier['status'] for barrier in barriers_cursor}

        # Attach 'status' to each zone entry
        for zone in zones:
            zone['status'] = status_map.get(zone['zone'], 'N/A')

        def get_nested_field(data, field_path):
            fields = field_path.split('.')
            for field in fields:
                if isinstance(data, dict):
                    data = data.get(field, None)
                else:
                    data = None
            return data

        zones.sort(
            key=lambda x: get_nested_field(x, sort_field_mongo) or '',
            reverse=(sort_order == -1)
        )

        # Handle AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return app.response_class(
                json_util.dumps({'zones': zones}),
                mimetype='application/json'
            )

        # Render the template with the zones data
        return render_template('real_time_data.html', zones=zones)

    except Exception as e:
        print(f"Error fetching data from MongoDB: {e}")
        return render_template('error.html', message="An error occurred while fetching data from the database.")


@app.route('/RealTime/download', methods=['GET'])
def download_real_time_data():
    try:
        # Aggregation pipeline to get the latest entry per zone
        pipeline = [
            {'$sort': {'time': -1}},  # Sort by 'time' descending
            {
                '$group': {
                    '_id': '$zone',
                    'zone': {'$first': '$zone'},
                    'time': {'$first': '$time'},
                    'sensors': {'$first': '$sensors'},
                    'DEVICE_ID': {'$first': '$DEVICE_ID'}
                }
            }
        ]
        zones_cursor = zone_collection.aggregate(pipeline)
        zones = list(zones_cursor)

        barriers_cursor = barriers_collection.find({}, {'zone': 1, 'status': 1})
        status_map = {barrier['zone']: barrier['status'] for barrier in barriers_cursor}

        for zone in zones:
            zone['status'] = status_map.get(zone['zone'], 'N/A')

        # Return the JSON data for download
        return jsonify(zones)

    except Exception as e:
        print(f"Error fetching data for download: {e}")
        return jsonify({"error": "An error occurred while fetching data"}), 500


""" Control Panel Page"""


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


@app.route('/control_panel', methods=['GET'])
@basic_auth.required
def control_panel():
    try:
        # Reading data from the barriers collection
        barriers_cursor = barriers_collection.find()
        barriers = list(barriers_cursor)

        pipeline = [
            {
                '$sort': {'time': -1}  # Sort by 'time' in descending order
            },
            {
                '$group': {
                    '_id': '$zone',
                    'zone': {'$first': '$zone'},
                    'time': {'$first': '$time'},
                    'sensors': {'$first': '$sensors'},
                    'DEVICE_ID': {'$first': '$DEVICE_ID'}
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


@app.route('/control_barrier', methods=['POST'])
def control_barrier():
    data = request.json
    print(f"Received request to control barrier: {data}")

    barrier_id = data['barrier_id']
    action = data['action']
    zone = data['zone']
    time = datetime.now()
    request_id = uuid.uuid4()
    id_str = str(request_id)

    # Publish MQTT message with the correct topic and payload
    topic_barrier_control = f"{MQTT_BARRIER_CONTROL_L}{zone}{MQTT_BARRIER_CONTROL_R}{barrier_id}"
    payload = json.dumps({
        'id': 'Server',
        'type': 'command',
        'data': action,
        'time': str(time),
        'id_request': id_str
    })

    client.publish(topic_barrier_control, payload)
    print(f"Published to MQTT topic {topic_barrier_control} with payload {payload}")

    insert_request = {
        'id_request': id_str,
        'barrier_id': barrier_id,
        'type': 'command',
        'data': action,
        'time': time,
        'status': 'failed',
        'outcome': 'failed'
    }

    try:
        result = requests_collection.insert_one(insert_request)
        print(f"Data Barrier inserted into MongoDB with object ID: {result.inserted_id}")
    except Exception as e:
        print(f'Error while inserting data into database: {e}')
        return jsonify({'status': 'error', 'message': 'Failed to record barrier command'}), 500

    return jsonify({'status': 'success', 'request_id': id_str, 'message': f"Barrier {barrier_id} control command sent"})


@app.route('/check_barrier_status', methods=['GET'])
def check_barrier_status():
    request_id = request.args.get('request_id')

    try:
        result = requests_collection.find_one({'id_request': request_id})
        if result and result.get('status') == 'completed':
            return jsonify({'status': 'completed'})
        elif result and result.get('status') == 'failed':
            return jsonify({'status': 'failed'})
        else:
            return jsonify({'status': 'failed'})

    except Exception as e:
        print(f"Error checking barrier status: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/notify', methods=['POST'])
def notify():
    data = request.get_json()
    print(f"Notification received: {data}")  # Mock logging to console
    return jsonify({"status": "success", "message": "Notification received"}), 200


# Example usage
if __name__ == '__main__':
    app.run(debug=True)
