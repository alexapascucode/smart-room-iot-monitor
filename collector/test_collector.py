import sqlite3
import tempfile
import unittest
from pathlib import Path

from collector import format_status, insert_telemetry, open_database, parse_telemetry


VALID_PAYLOAD = """{
  "device_id": "room-node-01",
  "temperature_c": 23.7,
  "humidity_pct": 51.2,
  "heat_index_c": 23.54,
  "rssi_dbm": -48,
  "uptime_s": 127
}"""


class TelemetryTests(unittest.TestCase):
    def test_parse_valid_payload(self):
        telemetry = parse_telemetry(VALID_PAYLOAD)
        self.assertEqual(telemetry.device_id, "room-node-01")
        self.assertAlmostEqual(telemetry.temperature_c, 23.7)
        self.assertEqual(telemetry.rssi_dbm, -48)

    def test_rejects_missing_field(self):
        with self.assertRaises(ValueError):
            parse_telemetry('{"device_id":"room-node-01"}')

    def test_rejects_invalid_humidity(self):
        bad = VALID_PAYLOAD.replace('51.2', '140.0')
        with self.assertRaises(ValueError):
            parse_telemetry(bad)

    def test_alert_formatting(self):
        telemetry = parse_telemetry(VALID_PAYLOAD.replace('23.7', '31.2', 1))
        text = format_status(telemetry, max_temp=28.0, max_humidity=70.0)
        self.assertIn("ALERT", text)
        self.assertIn("temperature above", text)

    def test_database_insert(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db = open_database(Path(temp_dir) / "test.db")
            telemetry = parse_telemetry(VALID_PAYLOAD)
            insert_telemetry(db, telemetry)
            row = db.execute("SELECT device_id, temperature_c FROM telemetry").fetchone()
            self.assertEqual(row[0], "room-node-01")
            self.assertAlmostEqual(row[1], 23.7)
            db.close()


if __name__ == "__main__":
    unittest.main()
