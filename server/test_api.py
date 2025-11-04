import requests
import time

URL_BASE = "http://localhost:8000/api/v0/"

def test_call(url):
    fullurl = URL_BASE + url
    print("Test call to:   ", fullurl)
    r = requests.get(fullurl)
    # print(r)
    print(r.text)
    print("")


test_call("oracle/oracle_info")

test_call("oracle/oracle_status")

test_call("event/event_classes")

now = int(time.time())
start_time1 = now + 7 * 24*3600
end_time1 = start_time1 + 2 * 24*3600
test_call("event/events?start_time={}&end_time={}&definition=btceur".format(start_time1, end_time1))

test_call("event/event_ids?start_time={}&end_time={}".format(start_time1, end_time1))

test_call("event/event_ids?start_time={}&end_time={}&definition=btceur".format(start_time1, end_time1))

test_call(f"event/next_event?definition=btceur&period={86400}")

start_time_past = now - 2 * 24*3600
test_call("event/events?start_time={}&end_time={}&definition=btceur".format(start_time_past, now))

# Past event with outcome
test_call("event/event/btceur1730934120")

test_call("price/current_all")

test_call("price/current/btceur")

test_call("price_info/current_all")

test_call("price_info/current/btceur")

# To demonstrate dummy_outcome_for_event, we need a future event, we need to construct a future ID
future_id = 1704067200 + (int((now - 1704067200) / 43200)) * 43200 + 5 * 43200
test_call("event/event/btceur{}".format(future_id))
test_call("test_only/dummy_outcome_for_event/btceur{}".format(future_id))
test_call("event/event/btceur{}".format(future_id))
