from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any



@dataclass(frozen=True)
class Telemetry:
    device_id: str
    temperature_c: float
    humidity_pct: float
    heat_index_c: float
    rssi_dbm: int
    uptime_s: int


def parse_telemetry(payload: bytes | str) -> Telemetry:
    """Parse and validate one MQTT telemetry payload."""
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")

    data: dict[str, Any] = json.loads(payload)
    required = {
        "device_id",
        "temperature_c",
        "humidity_pct",
        "heat_index_c",
        "rssi_dbm",
        "uptime_s",
    }
    missing = required.difference(data)
    if missing:
        raise ValueError(f"missing fields: {', '.join(sorted(missing))}")

    telemetry = Telemetry(
        device_id=str(data["device_id"]),
        temperature_c=float(data["temperature_c"]),
        humidity_pct=float(data["humidity_pct"]),
        heat_index_c=float(data["heat_index_c"]),
        rssi_dbm=int(data["rssi_dbm"]),
        uptime_s=int(data["uptime_s"]),
    )

    if not telemetry.device_id.strip():
        raise ValueError("device_id cannot be empty")
    if not -40.0 <= telemetry.temperature_c <= 85.0:
        raise ValueError("temperature_c outside DHT22 operating range")
    if not 0.0 <= telemetry.humidity_pct <= 100.0:
        raise ValueError("humidity_pct must be between 0 and 100")
    if telemetry.uptime_s < 0:
        raise ValueError("uptime_s cannot be negative")

    return telemetry


def open_database(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            received_at TEXT NOT NULL,
            device_id TEXT NOT NULL,
            temperature_c REAL NOT NULL,
            humidity_pct REAL NOT NULL,
            heat_index_c REAL NOT NULL,
            rssi_dbm INTEGER NOT NULL,
            uptime_s INTEGER NOT NULL
        )
        """
    )
    connection.commit()
    return connection


def insert_telemetry(connection: sqlite3.Connection, telemetry: Telemetry) -> None:
    connection.execute(
        """
        INSERT INTO telemetry (
            received_at, device_id, temperature_c, humidity_pct,
            heat_index_c, rssi_dbm, uptime_s
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(),
            telemetry.device_id,
            telemetry.temperature_c,
            telemetry.humidity_pct,
            telemetry.heat_index_c,
            telemetry.rssi_dbm,
            telemetry.uptime_s,
        ),
    )
    connection.commit()


def format_status(telemetry: Telemetry, max_temp: float, max_humidity: float) -> str:
    alerts: list[str] = []
    if telemetry.temperature_c > max_temp:
        alerts.append(f"temperature above {max_temp:.1f} C")
    if telemetry.humidity_pct > max_humidity:
        alerts.append(f"humidity above {max_humidity:.1f}%")

    message = (
        f"[{telemetry.device_id}] {telemetry.temperature_c:.1f} C | "
        f"{telemetry.humidity_pct:.1f} %RH | RSSI {telemetry.rssi_dbm} dBm"
    )
    if alerts:
        message += "  ALERT: " + "; ".join(alerts)
    return message


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MQTT telemetry collector for the Smart Room Monitor")
    parser.add_argument("--broker", default="test.mosquitto.org")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--topic", default="alex/smart-room/telemetry")
    parser.add_argument("--database", type=Path, default=Path("telemetry.db"))
    parser.add_argument("--max-temp", type=float, default=28.0)
    parser.add_argument("--max-humidity", type=float, default=70.0)
    return parser


def main() -> None:
    import paho.mqtt.client as mqtt

    args = build_parser().parse_args()
    db = open_database(args.database)

    def on_connect(client: mqtt.Client, userdata: object, flags: dict, reason_code: int, properties=None) -> None:
        print(f"Connected to {args.broker}:{args.port}; subscribing to {args.topic}")
        client.subscribe(args.topic, qos=1)

    def on_message(client: mqtt.Client, userdata: object, message: mqtt.MQTTMessage) -> None:
        try:
            telemetry = parse_telemetry(message.payload)
            insert_telemetry(db, telemetry)
            print(format_status(telemetry, args.max_temp, args.max_humidity))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            print(f"Rejected invalid payload: {exc}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="smart-room-collector")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.broker, args.port, keepalive=60)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nStopping collector")
    finally:
        db.close()
        client.disconnect()


if __name__ == "__main__":
    main()
