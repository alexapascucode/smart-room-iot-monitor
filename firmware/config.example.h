#pragma once

// Copy this file to config.h and replace the placeholder values.
// config.h is ignored by Git so credentials are not committed.

const char* WIFI_SSID = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

const char* MQTT_HOST = "test.mosquitto.org";
const uint16_t MQTT_PORT = 1883;
const char* MQTT_USER = "";
const char* MQTT_PASSWORD = "";

const char* DEVICE_ID = "room-node-01";
const char* TELEMETRY_TOPIC = "alex/smart-room/telemetry";
const char* STATUS_TOPIC = "alex/smart-room/status";
