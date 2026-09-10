#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include "config.h"

#define DHTPIN D4
#define DHTTYPE DHT22

constexpr unsigned long SAMPLE_INTERVAL_MS = 5000;
constexpr unsigned long RECONNECT_INTERVAL_MS = 3000;

DHT dht(DHTPIN, DHTTYPE);
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

unsigned long lastSampleMs = 0;
unsigned long lastWifiAttemptMs = 0;
unsigned long lastMqttAttemptMs = 0;

void connectWiFiNonBlocking() {
  if (WiFi.status() == WL_CONNECTED) return;

  const unsigned long now = millis();
  if (now - lastWifiAttemptMs < RECONNECT_INTERVAL_MS) return;
  lastWifiAttemptMs = now;

  Serial.printf("Connecting to Wi-Fi: %s\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void connectMqttNonBlocking() {
  if (WiFi.status() != WL_CONNECTED || mqttClient.connected()) return;

  const unsigned long now = millis();
  if (now - lastMqttAttemptMs < RECONNECT_INTERVAL_MS) return;
  lastMqttAttemptMs = now;

  Serial.printf("Connecting to MQTT broker %s:%u\n", MQTT_HOST, MQTT_PORT);

  bool connected;
  if (strlen(MQTT_USER) > 0) {
    connected = mqttClient.connect(
      DEVICE_ID,
      MQTT_USER,
      MQTT_PASSWORD,
      STATUS_TOPIC,
      1,
      true,
      "offline"
    );
  } else {
    connected = mqttClient.connect(
      DEVICE_ID,
      STATUS_TOPIC,
      1,
      true,
      "offline"
    );
  }

  if (connected) {
    mqttClient.publish(STATUS_TOPIC, "online", true);
    Serial.println("MQTT connected");
  } else {
    Serial.printf("MQTT connection failed, state=%d\n", mqttClient.state());
  }
}

void publishTelemetry() {
  const float humidity = dht.readHumidity();
  const float temperatureC = dht.readTemperature();

  if (isnan(humidity) || isnan(temperatureC)) {
    Serial.println("DHT22 read failed; skipping sample");
    return;
  }

  const float heatIndexC = dht.computeHeatIndex(temperatureC, humidity, false);

  char payload[256];
  snprintf(
    payload,
    sizeof(payload),
    "{\"device_id\":\"%s\",\"temperature_c\":%.2f,\"humidity_pct\":%.2f,"
    "\"heat_index_c\":%.2f,\"rssi_dbm\":%d,\"uptime_s\":%lu}",
    DEVICE_ID,
    temperatureC,
    humidity,
    heatIndexC,
    WiFi.RSSI(),
    millis() / 1000UL
  );

  if (mqttClient.publish(TELEMETRY_TOPIC, payload, false)) {
    Serial.println(payload);
  } else {
    Serial.println("MQTT publish failed");
  }
}

void setup() {
  Serial.begin(115200);
  delay(50);
  dht.begin();

  mqttClient.setServer(MQTT_HOST, MQTT_PORT);
  mqttClient.setKeepAlive(30);
  mqttClient.setBufferSize(512);

  connectWiFiNonBlocking();
}

void loop() {
  connectWiFiNonBlocking();
  connectMqttNonBlocking();

  if (mqttClient.connected()) {
    mqttClient.loop();
  }

  const unsigned long now = millis();
  if (now - lastSampleMs >= SAMPLE_INTERVAL_MS) {
    lastSampleMs = now;

    if (mqttClient.connected()) {
      publishTelemetry();
    }
  }
}
