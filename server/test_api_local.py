from oracle import EventStorageDb
from test_common import PriceSourceMockConstant, prepare_test_secret_for_cryptlib, recreate_empty_db_file

from datetime import datetime, UTC
from fastapi.testclient import TestClient
import os
import unittest


class ServerApiTestClass(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("setUpClass")

        prepare_test_secret_for_cryptlib()

        datadir = "/tmp"
        os.environ["DB_DIR"] = datadir
        recreate_empty_db_file(datadir + "/ora.db")

        # Trick here: only import these after setting up the secret file
        from main import app, oracle_app

        price_mock = PriceSourceMockConstant(98765)
        cls.client = TestClient(app=app)

        # Overrides
        # Re-create EventStoreDb, with specified datadir
        oracle_app.oracle.db = EventStorageDb(data_dir=datadir)
        # Overwrite the price source inside the app
        oracle_app.oracle.price_source = price_mock
        # Fill with default data for, for the test
        oracle_app.oracle.test_initialize_with_default_data(oracle_app.oracle.public_key)
        print("Server started")

    # def tearDown(self):
    #     print("tearDown")

    # def tearDownClass():
    #     print("tearDownClass")

    def test_oracle_info(self):
        response = self.client.get("/api/v0/oracle/oracle_info")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'horizon_days': 390.0,
            "main_public_key":"0330d54fd0dd420a6e5f8d3624f5f3482cae350f79d5f0753bf5beef9c2d91af3c",
            "public_keys": ["0330d54fd0dd420a6e5f8d3624f5f3482cae350f79d5f0753bf5beef9c2d91af3c"]
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

    def test_event_ids(self):
        now = round(datetime.now(UTC).timestamp())
        start_time1 = now - 5 * 86400
        end_time1 = now + 5 * 86400
        start_time2 = now - 200 * 86400
        end_time2 = now + 200 * 86400

        response = self.client.get(f"/api/v0/event/event_ids?start_time={start_time1}&end_time={end_time1}&definition=btcusd")
        self.assertEqual(response.status_code, 200)
        c = response.json()
        self.assertEqual(len(c), 721)

        response = self.client.get(f"/api/v0/event/event_ids?start_time={start_time1}&end_time={end_time1}")
        self.assertEqual(response.status_code, 200)
        c = response.json()
        self.assertEqual(len(c), 732)

        response = self.client.get(f"/api/v0/event/event_ids?start_time={start_time1}&definition=btcusd")
        self.assertEqual(response.status_code, 200)
        c = response.json()
        self.assertEqual(len(c), 5000)

        response = self.client.get(f"/api/v0/event/event_ids?end_time={end_time1}&definition=btcusd")
        self.assertEqual(response.status_code, 200)
        c = response.json()
        self.assertEqual(len(c), 721)

        response = self.client.get(f"/api/v0/event/event_ids?start_time={start_time1}")
        self.assertEqual(response.status_code, 200)
        c = response.json()
        self.assertEqual(len(c), 5000)

        response = self.client.get(f"/api/v0/event/event_ids?end_time={end_time1}")
        self.assertEqual(response.status_code, 200)
        c = response.json()
        self.assertEqual(len(c), 732)

        response = self.client.get(f"/api/v0/event/event_ids?definition=btcusd")
        self.assertEqual(response.status_code, 200)
        c = response.json()
        self.assertEqual(len(c), 5000)

        response = self.client.get(f"/api/v0/event/event_ids")
        self.assertEqual(response.status_code, 200)
        c = response.json()
        self.assertEqual(len(c), 5000)

        response = self.client.get(f"/api/v0/event/event_ids?start_time={start_time2}&end_time={end_time2}&definition=btcusd")
        self.assertEqual(response.status_code, 200)
        c = response.json()
        self.assertEqual(len(c), 5000)


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

    # Note: depends on network, remote server
    def test_price_info(self):
        response = self.client.get("/api/v0/price_info/current/btcusd")
        self.assertEqual(response.status_code, 200)
        json_value = response.json()
        # print(json_value)

        value = json_value["price"]
        # print(value)
        self.assertGreater(value, 9_999)
        self.assertLess(value, 99_999_999)

        self.assertEqual(json_value["symbol"], "BTCUSD")

        self.assertEqual(json_value["error"], None)

        retrieve_time = json_value["retrieve_time"]
        now = datetime.now(UTC).timestamp()
        age = now - retrieve_time
        # print(age, retrieve_time, now)
        self.assertGreater(age, -300)
        self.assertLess(age, 300)

if __name__ == "__main__":
    unittest.main() # run all tests

