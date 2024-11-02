#include <ArduinoJson.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <ESP8266HTTPClient.h> 
#include <SoftwareSerial.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

// ---------------------- Configuration ----------------------

// WiFi Configuration
#define SSID_WIFI "Redmipod"
#define PASSWORD_WIFI "12345678"

// MQTT Configuration
const char* MQTT_SERVER = "test.mosquitto.org";
const char* MQTT_CLIENT_NAME = "ArduinoClient_1";
const int MQTT_PORT = 1883;
String MQTT_TOPIC_BASE = "IoTAQStation";

// Map Source URL
// String map_source = "http://192.168.1.145:8080/GetZones";  // Local
String map_source = "http://ilpodd2.pythonanywhere.com/GetZones"; // Online

// Maximum number of zones
#define N 10

// Serial Communication Configuration
static const uint32_t ucBaud = 9600;
SoftwareSerial Serial_Arduino(D6, D5); // RX, TX

// Timing Variables
int GPS_seconds = 5;
unsigned long start_time = millis();
unsigned long timeout = 10000;  // 10 seconds

// Flags
int flag_gps = 0;
int flag_sens = 0;

// ---------------------- Struct Definition ----------------------

// Define the Zone  globally
typedef struct {
  double x_c;
  double y_c;
  double side;
  String name;
} Zona;

// ---------------------- Global Variables ----------------------

// Zone Management Variables
String actual_zone = "out";
String prev_zone = "out";
int zone_length;
Zona zone[N]; // Array to hold zone data

// JSON Document for Map Data
StaticJsonDocument<2000> doc;

// MQTT Client Setup
WiFiClient espClient;
PubSubClient client(espClient);

// HTTP Client for Map Retrieval
HTTPClient http;

// GPS Boundary Variables
double lat_min;
double lat_max;
double long_min;
double long_max;

// Device Identification
String DEVICE_ID = "ID_01";

// ---------------------- Functions Declaration ----------------------
Zona* map_memory_inizialization(Zona* zone);
String requestMap(String map_src);
String check_zone(double x_position, double y_position, Zona* zone);
void bounds_extractor(Zona* zone);
void setup_wifi();
bool isWiFiConnected();
bool ConnectMqtt();
void InitMqtt();
void OnMqttReceived(char *topic, byte *payload, unsigned int length);
void SubscribeMqtt(String topic);
void UnsubscribeMqtt(String topic);
bool isMqttConnected();
void HandleMqtt();
bool PublishMqtt(String topic, String message);
void clearSerialBuffer(SoftwareSerial &serial);
void reconnectWiFi();

// ---------------------- Setup Function ----------------------
void setup() {  
    // Initialize Serial Communications
    Serial.begin(9600);
    Serial_Arduino.begin(9600);
    Serial.println("Starting with setup..");
    
    // Connect to WiFi
    setup_wifi();  
    
    // Verify WiFi Connection
    while(!isWiFiConnected()) {
        Serial.println("WiFi not connected. Retrying...");
        reconnectWiFi();
    }
    
    // Request and Deserialize Map JSON
    String zones_map = requestMap(map_source);
    while(zones_map == "") {
        Serial.println("Map download failed. Retrying the download.");
        zones_map = requestMap(map_source);
    }
    Serial.println("Downloading the map was successful.");      
    deserializeJson(doc, zones_map);      
    zone_length = doc.size();
    
    // Initialize Map Memory
    map_memory_inizialization(zone);
    if(zone != NULL) {
        bounds_extractor(zone);
    }
    else { 
        Serial.println("ERROR: The static memory associated with the map is insufficient. Re-initialization is required."); 
    }
    bool map_check = true; 
    
    // Debug Output
    Serial.println(zones_map);
    
    // Initialize MQTT
    InitMqtt();
    while(!ConnectMqtt());
    Serial.println("Connected to MQTT Server: "+ String(MQTT_SERVER));
    Serial.println("Setup Terminated!");
}

// ---------------------- Loop Function ----------------------
void loop() {
    // Ensure MQTT is connected
    HandleMqtt();

    // Delay between GPS readings
    delay(GPS_seconds * 1000);

    // -------------------- GPS Data Acquisition --------------------
    
    Serial_Arduino.println("gps");
    Serial.println("Sent command: 'gps'");

    double latitude = 0.0, longitude = 0.0;
    bool gps_success = false;

    unsigned long start_time = millis();

    // Wait for <start>
    while (millis() - start_time < timeout) {
        if (Serial_Arduino.available()) {
            String line = Serial_Arduino.readStringUntil('\n');
            line.trim();
            if (line == "<start>") {
                // Read latitude
                String lat_line = Serial_Arduino.readStringUntil('\n');
                lat_line.trim();
                // Read longitude
                String lng_line = Serial_Arduino.readStringUntil('\n');
                lng_line.trim();
                // Read <end>
                String end_line = Serial_Arduino.readStringUntil('\n');
                end_line.trim();

                if (end_line == "<end>") {
                    if (lat_line.startsWith("lat:") && lng_line.startsWith("lng:")) {
                        latitude = lat_line.substring(4).toDouble();
                        longitude = lng_line.substring(4).toDouble();
                        Serial.println("GPS Latitude: " + String(latitude));
                        Serial.println("GPS Longitude: " + String(longitude));
                        gps_success = true;
                    } else {
                        Serial.println("ERROR: Invalid GPS data format.");
                    }
                }
                break;
            }
        }
        delay(10);
    }

    if (!gps_success) {
        Serial.println("ERROR: Timeout or invalid response for GPS data.");
        return;
    }

    // Determine the current zone based on GPS coordinates
    actual_zone = check_zone(latitude, longitude, zone);
    Serial.println("Current Zone: " + actual_zone);

    // -------------------- AQM Data Acquisition --------------------
    Serial_Arduino.println("aq");
    Serial.println("Sent command: 'aq'");

    float humidity, temperature, aqm;
    bool aq_success = false;

    start_time = millis();

    // Wait for <start>
    while (millis() - start_time < timeout) {
        if (Serial_Arduino.available()) {
            String line = Serial_Arduino.readStringUntil('\n');
            line.trim();
            if (line == "<start>") {
                // Read humidity
                String hum_line = Serial_Arduino.readStringUntil('\n');
                hum_line.trim();
                // Read temperature
                String temp_line = Serial_Arduino.readStringUntil('\n');
                temp_line.trim();
                // Read AQM
                String aqm_line = Serial_Arduino.readStringUntil('\n');
                aqm_line.trim();
                // Read <end>
                String end_line = Serial_Arduino.readStringUntil('\n');
                end_line.trim();

                if (end_line == "<end>") {
                    if (hum_line.startsWith("humidity:") && temp_line.startsWith("temperature:") && aqm_line.startsWith("aqm:")) {
                        humidity = hum_line.substring(9).toFloat();
                        temperature = temp_line.substring(12).toFloat();
                        aqm = aqm_line.substring(4).toFloat();
                        Serial.println("Humidity: " + String(humidity));
                        Serial.println("Temperature: " + String(temperature));
                        Serial.println("AQM: " + String(aqm));
                        aq_success = true;
                    } else {
                        Serial.println("ERROR: Invalid AQ data format.");
                    }
                }
                break;
            }
        }
        delay(10);
    }

    if (!aq_success) {
        Serial.println("ERROR: Timeout or invalid response for AQ data.");
        return;
    }

  // -------------------- MQTT Topic Management --------------------
  // Check if the zone has changed
  if (actual_zone != prev_zone) {
      // Unsubscribe from the previous zone topic if not "out"
      if (prev_zone != "out") {
          String prev_topic = MQTT_TOPIC_BASE + "/Zones/" + prev_zone + "/Devices/" + DEVICE_ID;
          UnsubscribeMqtt(prev_topic);
          Serial.println("Unsubscribed from previous topic: " + prev_topic);
      }

      // Subscribe to the new zone topic if it is not "out"
      if (actual_zone != "out") {
          String new_topic = MQTT_TOPIC_BASE + "/Zones/" + actual_zone + "/Devices/" + DEVICE_ID;
          SubscribeMqtt(new_topic);
          Serial.println("Subscribed to new topic: " + new_topic);
      }

      // Update the previous zone
      prev_zone = actual_zone;
  }

// -------------------- MQTT Publishing --------------------
if (isMqttConnected()) {
    String topic_to_publish = MQTT_TOPIC_BASE + "/Zones/" + actual_zone + "/Devices/" + DEVICE_ID;
    String message = "{ \"type\": \"measurement\", "
                    "\"Latitude\": " + String(latitude, 6) + ", "
                    "\"Longitude\": " + String(longitude, 6) + ", "
                    "\"Zone\": \"" + actual_zone + "\", "
                    "\"Temperature\": " + String(temperature) + ", "
                    "\"Humidity\": " + String(humidity) + ", "
                    "\"AQM\": " + String(aqm) + " }";


    if (PublishMqtt(topic_to_publish, message)) {
        Serial.println("MQTT Message Published Successfully to " + topic_to_publish);
    } else {
        Serial.println("ERROR: MQTT Message Publishing Failed.");
    }
} else {
    Serial.println("ERROR: MQTT Not Connected.");
}
delay(1000);
}


// ---------------------- Function Definitions ----------------------

// Initialize Map Memory
Zona* map_memory_inizialization(Zona* zone) {
    if(zone_length > N) {
        Serial.println("ERROR: zone_length exceeds N");
        return NULL;
    }
    Serial.println("Memory initialization..");
    for (int i = 0 ; i < zone_length ; i++) {
        zone[i].x_c    =   (double)doc[i][0];
        zone[i].y_c    =   (double)doc[i][1];
        zone[i].side   =   (double)doc[i][2];
        zone[i].name   =   String((const char*)doc[i][3]);
    }
    Serial.println("Memory initialized successfully!");
    for (int i = 0 ; i < zone_length ; i++) {
        Serial.print("Zona ");
        Serial.println((i+1));
        Serial.println(zone[i].x_c,6);     
        Serial.println(zone[i].y_c,6); 
        Serial.println(zone[i].side,6);
        Serial.println(zone[i].name);
    }
    return zone;
}

// Request Map JSON from Server
String requestMap(String map_src) {  
    Serial.println("Map requesting....");
    String payload;
    http.begin(espClient, map_src);
    Serial.print("[HTTP] GET...\n");
    // http.GET sends the request and receives the response code
    int httpCode = http.GET();
    // httpCode will be negative on external error, such as no connection
    if (httpCode > 0) {
        // HTTP header has been sent and Server response header has been handled 
        Serial.printf("[HTTP] GET... code: %d\n", httpCode);
        payload = http.getString();
        Serial.println(payload);
        // File found at server 
        if (httpCode == HTTP_CODE_OK || httpCode == HTTP_CODE_MOVED_PERMANENTLY) {
            // NB: HTTP_CODE_MOVED_PERMANENTLY means that the resource exists
            Serial.println("I received an OK response");
        }
    }
    else {
        Serial.printf("[HTTP] GET,error: %s\n", http.errorToString(httpCode).c_str()); 
        return ""; 
    }
    return payload;
}

// Check Current Zone Based on GPS Position
String check_zone(double x_position, double y_position, Zona* zone) {
    double x_c, y_c, l;
    String zone_name; 
    for(int i = 0; i < zone_length; i++) {
        x_c = zone[i].x_c;
        y_c = zone[i].y_c;
        l   = zone[i].side;
        zone_name  = zone[i].name;
        if(((x_c + l) >= x_position) && ((x_c - l) <= x_position) && 
           ((y_c + l) >= y_position) && ((y_c - l) <= y_position))
            return zone_name;
    }
    return "out";
}

// Extract Boundaries from Zones
void bounds_extractor(Zona* zone) {
    // LAT min-max
    Serial.println("Extracting boundaries...");
    Serial.println(zone[0].x_c);
    lat_min = zone[0].x_c - zone[0].side / 2;
    lat_max = zone[0].x_c + zone[0].side / 2;
    for (int i  = 1; i < zone_length ; i++) { 
        if ((zone[i].x_c - zone[i].side / 2) < lat_min)
            lat_min = (zone[i].x_c - zone[i].side / 2);
        if ((zone[i].x_c + zone[i].side / 2) > lat_max)
            lat_max = (zone[i].x_c + zone[i].side / 2);
    }
    // LONG min-max
    long_min = zone[0].y_c - zone[0].side / 2;
    long_max = zone[0].y_c + zone[0].side / 2;
    for (int i  = 1; i < zone_length ; i++) { 
        if ((zone[i].y_c - zone[i].side / 2) < long_min)
            long_min = (zone[i].y_c - zone[i].side / 2);
        if ((zone[i].y_c + zone[i].side / 2) > long_max)
            long_max = (zone[i].y_c + zone[i].side / 2);
    }
    Serial.println("Boundary extraction completed.");
    Serial.print("Latitude Min: "); Serial.println(lat_min,6);
    Serial.print("Latitude Max: "); Serial.println(lat_max,6);
    Serial.print("Longitude Min: "); Serial.println(long_min,6);
    Serial.print("Longitude Max: "); Serial.println(long_max,6);
}

// Connect to WiFi
void setup_wifi(){
    delay(10);
    Serial.println();
    Serial.print("Connecting to ");
    Serial.print(SSID_WIFI);
    WiFi.begin(SSID_WIFI ,PASSWORD_WIFI);
    while(WiFi.status() != WL_CONNECTED){
        delay(500); Serial.print("."); 
    }                                  
    Serial.println("");
    Serial.println("WiFi connected");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
}

// Reconnect to WiFi (if needed)
void reconnectWiFi()
{
    Serial.println("Trying to reconnect to ");
    Serial.print(SSID_WIFI);
    WiFi.begin(SSID_WIFI ,PASSWORD_WIFI);
    while(WiFi.status() != WL_CONNECTED){
        delay(500); 
        Serial.print("."); 
    }                                  
    Serial.println("");
    Serial.println("WiFi reconnected");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
}

// Check WiFi Connection Status
bool isWiFiConnected()
{
    return (WiFi.status() == WL_CONNECTED);
} 

// MQTT Callback Function
void OnMqttReceived(char *topic, byte *payload, unsigned int length)
{
    Serial.print("Received on ");
    Serial.print(topic);
    Serial.print(": ");

    String content = "";
    for (size_t i = 0; i < length; i++)
    {
        content += (char)payload[i];
    }
    Serial.println(content);
}

// Initialize MQTT
void InitMqtt()
{
    client.setServer(MQTT_SERVER, MQTT_PORT);
    client.setCallback(OnMqttReceived);
    // Attempt to connect immediately
    if (ConnectMqtt()) {
        Serial.println("MQTT Connected Successfully.");
    }
    else {
        Serial.println("Failed to connect to MQTT Broker.");
    }
}

// Subscribe to an MQTT Topic
void SubscribeMqtt(String topic)
{
    if(client.subscribe(topic.c_str())) {
        Serial.println("Subscribed to topic: " + topic);
    } else {
        Serial.println("ERROR: Failed to subscribe to topic: " + topic);
    }
}

// Unsubscribe from an MQTT Topic
void UnsubscribeMqtt(String topic)
{
    if(client.unsubscribe(topic.c_str())) {
        Serial.println("Unsubscribed from topic: " + topic);
    } else {
        Serial.println("ERROR: Failed to unsubscribe from topic: " + topic);
    }
}

// Connect to MQTT Broker
bool ConnectMqtt()
{
    if (client.connect(MQTT_CLIENT_NAME)) {
        Serial.println("Connected to MQTT Broker!");
        return true;
    } else {
        Serial.print("Failed to connect to MQTT Broker, state ");
        Serial.println(client.state());
        return false;
    }
} 

// Check MQTT Connection Status
bool isMqttConnected()
{
    return client.connected();
}  

// Handle MQTT Connection and Loop
void HandleMqtt()
{
    if (!isMqttConnected())
    {
        Serial.println("MQTT not connected. Attempting to connect...");
        if (ConnectMqtt()) {
            Serial.println("MQTT connected!");
           
        }
    }
    client.loop();
}     

// Publish Message to MQTT Topic
bool PublishMqtt(String topic, String message)
{
    return client.publish(topic.c_str(), message.c_str());
}

// Clear Serial Buffer
void clearSerialBuffer(SoftwareSerial &serial) {
    while (serial.available() > 0) {
        serial.read(); // Read and discard
    }
}

