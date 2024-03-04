from flask import Flask, request, jsonify, render_template, make_response
from parameters import geo_zones

from DatabaseManager import Database_manager
from credentials import *
from Classes import Zone
from datetime import datetime
import random, string
import paho.mqtt.client as mqtt
import json

app = Flask(__name__)
"""
db=Database_manager(db_name=db_name,uri=uri,port=port)
db.connect_db()
"""

"""FLASK APIs"""
"""----HOME PAGE-------"""


@app.route('/home', methods=['GET'])
@app.route('/index', methods=['GET'])
@app.route('/', methods=['GET'])
def home():
    return render_template('home.html')


"""--------GET ZONE GEODATA PAGE------------"""


@app.route('/GetZones', methods=['GET'])
def send_zones():
    response = make_response(jsonify(geo_zones))
    response.headers['Content-Type'] = 'text/plain'
    return response

"""---------REAL TIME AIR QUALITY PAGE"""


@app.route('/RealTime', methods=['GET'])
def history():
    return render_template('history.html')


"""---------REAL TIME AIR QUALITY PAGE"""


@app.route('/History', methods=['GET'])
def real_time():
    return render_template('real_time_data.html')


""" Control Panel Page"""


@app.route('/ControlPanel', methods=['GET'])
def control_panel():
    return render_template('control_panel.html')


"""MQTT"""

"""
def on_message(client, userdata, message):
    ON MESSAGE EVENT received


client_id = ''.join(random.choice(string.digits) for i in range(6))
client = mqtt.Client(client_id)
client.on_message = on_message
client.connect("70206d5bc3594fa6b6243858b66920be.s1.eu.hivemq.cloud", port=8883, keepalive=60)
client.subscribe(topic_base + "/" + topic_sensors + "/#")
client.loop_start()

"""
if __name__ == '__main__':
    app.run()
