from main import app, oracle_app
from test_common import PriceSourceMockConstant

from datetime import datetime, UTC
from fastapi.testclient import TestClient
import unittest


class ServerApiTestClass(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("setUpClass")
        price_mock = PriceSourceMockConstant(98765)
        cls.client = TestClient(app=app)
        # Overwrite the price source inside the app
        oracle_app.oracle.price_source = price_mock
        print("Server started")

    # def recreate_db(self):
    #     print(f"Temp DB used: {self.dbfile}")
    #     if os.path.isfile(self.dbfile):
    #         os.remove(self.dbfile)
    #     conn = sqlite3.connect(self.dbfile)
    #     db_ws.db_setup_1(conn)
    #     conn.close()

    def test_oracle_info(self):
        response = self.client.get("/api/v0/oracle/oracle_info")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "main_public_key":"0292892b831077bc87f7767215ab631ff56d881986119ff03f1b64362e9abc70cd",
            "public_keys": ["0292892b831077bc87f7767215ab631ff56d881986119ff03f1b64362e9abc70cd"]
        })

    def test_oracle_status(self):
        response = self.client.get("/api/v0/oracle/oracle_status")
        self.assertEqual(response.status_code, 200)
        c = response.json()

        self.assertTrue("current_time_utc" in c)
        time = float(c["current_time_utc"])
        now = datetime.now(UTC).timestamp()
        timediff = now - time
        # print(timediff)
        self.assertTrue(abs(timediff) < 5)

        self.assertTrue("future_event_count" in c)
        self.assertTrue("total_event_count" in c)
        self.assertTrue(int(c["total_event_count"]) >= 1000)

    def test_event_classes(self):
        response = self.client.get("/api/v0/event/event_classes")
        self.assertEqual(response.status_code, 200)
        c = response.json()
        # print(c)
        self.assertTrue(len(c) == 2)
        self.assertEqual(c[0]["class_id"], "btcusd")
        self.assertEqual(c[0]["desc"]["definition"], "BTCUSD")

    def test_next_event(self):
        response = self.client.get("/api/v0/event/event_classes")
        self.assertEqual(response.status_code, 200)
        c = response.json()
        event_class = c[0]["class_id"]
        event_def = c[0]["desc"]["definition"]

        now = datetime.now(UTC).timestamp()
        response = self.client.get(f"/api/v0/event/next_event?definition={event_def}&period=86400")
        self.assertEqual(response.status_code, 200)
        c = response.json()
        # print(c)
        self.assertTrue("event_id" in c)
        event_id = c["event_id"]
        self.assertTrue("time_utc" in c)
        event_time = c["time_utc"]
        target_time = now + 86400
        timediff = event_time - target_time
        # print(now, target_time, event_time, timediff)
        self.assertGreater(event_time, target_time)

        self.assertEqual(c["definition"], event_def)
        self.assertEqual(c["event_class"], event_class)
        self.assertTrue("signer_public_key" in c)
        self.assertTrue("nonces" in c)
        self.assertEqual(len(c["nonces"]), 7)
        self.assertEqual(c["has_outcome"], False)

        response = self.client.get(f"/api/v0/event/event/{event_id}")
        self.assertEqual(response.status_code, 200)
        c2 = response.json()
        # print(c2)
        self.assertEqual(c2, c)

    # Note: depends on network, remote server
    def test_price(self):
        response = self.client.get("/api/v0/price/current/btcusd")
        self.assertEqual(response.status_code, 200)
        value = float(response.text)
        print(value)
        self.assertGreater(value, 9_999)
        self.assertLess(value, 99_999_999)

if __name__ == "__main__":
    unittest.main() # run all tests

