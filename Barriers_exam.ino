
#include <Servo.h>
#include <ArduinoJson.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <ESP8266HTTPClient.h> 
#include <SoftwareSerial.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#define SSID_WIFI "Redmi"
#define PASSWORD_WIFI "occidentefinito"
#define BUFFER_SIZE 100
String status = "open";
String json_command;
Servo myServo;  
WiFiClient espClient;
PubSubClient client(espClient);
String message_received[BUFFER_SIZE];
String message_to_transmit[BUFFER_SIZE];
int first_received = 0;
int last_received = 0;
int first_to_transmit = 0;
int last_to_transmit  = 0;
const char* MQTT_SERVER = "test.mosquitto.org";
const char *MQTT_CLIENT_NAME = "Barrier_001";
String MQTT_TOPIC_BASE = "IoTAQStation";
String topic_barr = MQTT_TOPIC_BASE+"/Zones"+"/Parchetto"+"/Barriers"+"/"+String(MQTT_CLIENT_NAME);
StaticJsonDocument<200> doc;
const int   MQTT_PORT = 1883;
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
        Serial.println("WiFi connected");
        Serial.print("IP address: ");
        Serial.println(WiFi.localIP());
      }

void HandleWifi()
     {
        if(!isWiFiConnected())
          {
            reconnectWiFi();
          }

     }
bool isWiFiConnected()
    {
      return (WiFi.status() == WL_CONNECTED);
    } 
//CB-Procedure
void OnMqttReceived(char *topic, byte *payload, unsigned int length)
{
   
    String content = "";
    for (size_t i = 0; i < length; i++)
    {
        content.concat((char)payload[i]);
    }
    deserializeJson(doc,content);
    if(doc["id"] == "Server")
      {
       Serial.print("Received on ");
       Serial.print(topic);
       Serial.print(": ");
       message_received[last_received] = content;
       last_received = (last_received + 1) % BUFFER_SIZE;
       Serial.println(content);
      }
    
    
   
}

void InitMqtt()
{
    client.setServer(MQTT_SERVER, MQTT_PORT);
    client.setCallback(OnMqttReceived);
}

bool SubscribeMqtt(String topic)
    {
      return client.subscribe(topic.c_str());
    }

bool UnsubscribeMqtt(String topic)
    {
      return client.unsubscribe(topic.c_str());
    }
bool ConnectMqtt()
     {
      return client.connect(MQTT_CLIENT_NAME);
     } 
bool isMqttConnected()
    {
      return client.connected();
    }  
void HandleMqtt()
  {
    if (!isMqttConnected())
    {
       if(ConnectMqtt())
          Serial.println("Mqtt connected.");
       else
          Serial.println("Mqtt is not connected.");
    }
    client.loop();
  }     
bool PublishMqtt(String topic, String message)
    {
      return client.publish(topic.c_str(), message.c_str());
    }


void setup() {
  Serial.begin(9600);
  // Wifi configuration
  setup_wifi();
  // MQTT configuration
  InitMqtt();
  Serial.println("Connecting Mqtt...");
  while(!ConnectMqtt())
      {
        delay(500);
        Serial.print(".");
      
      }
  Serial.println("Mqtt connected. Server: "+String(MQTT_SERVER));
  Serial.println("Subscribing to the topic: "+String(topic_barr));
  while(!SubscribeMqtt(topic_barr));

  Serial.println("Successfully Subscribed. Topic:"+String(topic_barr));
  // Hardware configuration
  myServo.attach(D3);
  // Set-initial position
  myServo.write(0);
  close();
  open();

  
}

void open()
    { 
      int MAX_ANGLE = 180;
      if(status == "close")
        { 

          for (int angle = 0; angle <= MAX_ANGLE; angle++)
            myServo.write(angle);
          
          status = "open";
          message_to_transmit[last_to_transmit] = "open";
          last_to_transmit = (last_to_transmit + 1)% BUFFER_SIZE;

          
        }   
    }

void close()
    { 
      
      int MIN_ANGLE = 0;
      if(status == "open")
        {
          for (int angle = 180; angle >= 0; angle--)
             myServo.write(angle);
          status = "close";
          message_to_transmit[last_to_transmit] = "close";
          last_to_transmit = (last_to_transmit + 1)% BUFFER_SIZE;
        }
    
    }



void ManageCommunication()
    {
     if(isMqttConnected)
      {
     // Reception (ONLY COMMANDS ALLOWED)
     if(first_received != last_received)
        { 

          json_command =  message_received[first_received];
          first_received = (first_received + 1) % BUFFER_SIZE;
          deserializeJson(doc, json_command);
          if(String(doc["type"]) == "command")
              {
                 // Valid command 
                 if(doc["data"] == "open")
                    open();
                 if(doc["data"] == "close")
                    close();

              }
          
              
          

        }
       // Transmission (ONLY STATUS ALLOWED)
    if(first_to_transmit != last_to_transmit)
        { 
          String open_JS = "{";
          String close_JS = "}";
          String type     =  "\"type\" : \"status\", " ;
          String data     =  "\"data\" : \""+message_to_transmit[first_to_transmit]+"\",";
          String id_req   =  "\"id_req\" : "+String("\"")+String(doc["id_request"])+String("\"");      
          String message = open_JS + type + data + id_req + close_JS;
          PublishMqtt(topic_barr, message);
          first_to_transmit = (first_to_transmit + 1) % BUFFER_SIZE;
        }
      }
}

void loop() {

  HandleWifi();
  HandleMqtt();
  ManageCommunication();  

            }


