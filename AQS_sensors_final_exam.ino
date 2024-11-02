#include <DHT.h>
#include <AltSoftSerial.h>
#include <TinyGPS++.h>
#include <SoftwareSerial.h>
#include <MQ135.h>

// Initialize DHT11 sensor
#define DHTPIN 2                                                                                                       
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

MQ135 mq135_sensor(A0); // MQ135 connected to analog pin A0
boolean flag=false;
// Initialize GPS
TinyGPSPlus gps;
AltSoftSerial gpsSerial; // Automatically uses pins 8 (RX) and 9 (TX) for GPS

// Communication with NodeMCU
SoftwareSerial espSerial(12, 13); // NodeMCU connected to pins 12 (RX) and 13 (TX)

void setup() {
  Serial.begin(9600);          // Serial Monitor
  espSerial.begin(9600);       // Communication with NodeMCU
  Serial.println("ESP Initialized");
  gpsSerial.begin(9600);       // Communication with GPS module
  Serial.println("GPS Initialized");
  dht.begin();                 // Initialize DHT sensor
  Serial.println("DHT Initialized");
}

void loop() {
    // Read data from GPS module
    while (gpsSerial.available() > 0) {
        gps.encode(gpsSerial.read());
    }
    if (gps.location.isValid() & flag==false)
    {
      Serial.print("GPS position found!");
      flag= true;
    }

    // Handle commands from NodeMCU
    if (espSerial.available() > 0) {
        String command = espSerial.readStringUntil('\n');
        command.trim(); // Remove any whitespace or newline characters

        if (command == "gps") {
            espSerial.println("<start>");
            if (gps.location.isValid()) {
                espSerial.println("lat:" + String(gps.location.lat(), 6));
                espSerial.println("lng:" + String(gps.location.lng(), 6));
            } else {
                espSerial.println("lat:err");
                espSerial.println("lng:err");
            }
            espSerial.println("<end>");
        } 
        else if (command == "aq") {
            float humidity = dht.readHumidity();
            float temperature = dht.readTemperature();
            float correctedPPM = mq135_sensor.getCorrectedPPM(temperature, humidity);

            espSerial.println("<start>");
            espSerial.println("humidity:" + (isnan(humidity) ? "N/A" : String(humidity)));
            espSerial.println("temperature:" + (isnan(temperature) ? "N/A" : String(temperature)));
            espSerial.println("aqm:" + (isnan(correctedPPM) ? "N/A" : String(correctedPPM)));
            espSerial.println("<end>");
        }
    }

    delay(100); // Short delay to prevent overload
}

