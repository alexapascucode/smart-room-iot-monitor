## Resume / LinkedIn project blurb

**Smart Room IoT Monitor — ESP8266, C/C++, MQTT, Python, SQLite**
- Built ESP8266 firmware to sample DHT22 temperature/humidity data and publish structured MQTT telemetry with automatic reconnect handling.
- Developed a Python MQTT collector that validates sensor payloads, stores time-series readings in SQLite, and generates configurable threshold alerts.
- Added unit tests and GitHub Actions CI while keeping Wi-Fi/MQTT credentials out of source control.
