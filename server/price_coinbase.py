# Copyright (c) 2025-present Cadena Bitcoin
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from price_common import PriceInfoSingle

import asyncio
from datetime import datetime, UTC
import json
import threading
import websockets

# Get rate price info from Coinbase, through websockets.
# See https://docs.cdp.coinbase.com/exchange/websocket-feed/overview
class CoinbasePriceSource:
    def __init__(self):
        self.source_id = "Coinbase"
        self.uri = "wss://ws-feed.exchange.coinbase.com"
        self.channel = "ticker"
        self.cache = {}
        self.bg_thread = threading.Thread(target=self.run_websocket_listener, args=())
        self.bg_thread.start()
        print("CoinbasePriceSource: bg thread started")

        print(f"{self.source_id} price source initialized, uri {self.uri}")

    def get_source_id(self):
        return self.source_id

    # We are always fast/cached
    def get_price_info_fast(self, symbol: str, pref_max_age: float = 0) -> float | None:
        now = datetime.now(UTC).timestamp()

        symbol = symbol.upper()
        if symbol in self.cache:
            cached = self.cache[symbol]
            # print("Using cached value", cached.price, cached)
            return cached
        # Not cached, error
        return PriceInfoSingle.create_with_error(symbol, now, self.source_id, f"Price info not available, {symbol}, uri {self.uri}")

    def get_price_info(self, symbol: str, pref_max_age: float = 0) -> float:
        return self.get_price_info_fast(symbol, pref_max_age)

    def internal_symbols(self) -> list[str]:
        return ["BTC-USD", "BTC-EUR"]

    def internal_symbol(self, symbol) -> str:
        symbol = symbol.upper()
        if symbol == "BTCUSD":
            return "BTC-USD"
        if symbol == "BTCEUR":
            return "BTC-EUR"
        return None

    def symbol(self, int_symbol) -> str:
        int_symbol = int_symbol.upper()
        if int_symbol == "BTC-USD":
            return "BTCUSD"
        if int_symbol == "BTC-EUR":
            return "BTCEUR"
        return None

    def update_recvd(self, data):
        try:
            now = datetime.now(UTC).timestamp()
            # print(f"update_recvd {data}")
            if "product_id" in data and "price" in data and "time" in data:
                int_symbol = data["product_id"]
                symbol = self.symbol(int_symbol)
                if not symbol:
                    print(f"Error symbol mismatch '{symbol}'!")
                else:
                    price = float(data["price"])
                    time_obj = datetime.fromisoformat(data["time"])
                    time = time_obj.timestamp()
                    # print(symbol, price, time, time_obj.ctime())
                    # Create price info and store it
                    price_info = PriceInfoSingle(price, symbol, now, time, self.source_id)
                    self.cache[symbol] = price_info
            else:
                print(f"Not a price update message, or other error: {data}")
        except Exception as ex:
            print(f"Update exception: {data} {ex}")

    def run_websocket_listener(self):
        # print("run_websocket_listener")
        asyncio.run(self.websocket_listener())

    async def websocket_listener(self):
        # print("websocket_listener")
        timestamp = str(datetime.now(UTC).timestamp())
        product_ids = self.internal_symbols()
        # print(self.channel, product_ids, timestamp)
        subscribe_message = json.dumps({
            'type': 'subscribe',
            'channels': [{'name': self.channel, 'product_ids': product_ids}],
            'timestamp': timestamp
        })

        while True:
            try:
                async with websockets.connect(self.uri, ping_interval=None) as websocket:
                    await websocket.send(subscribe_message)
                    while True:
                        response = await websocket.recv()
                        json_response = json.loads(response)
                        # print(json_response)
                        self.update_recvd(json_response)

            except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK):
                print('Connection closed, retrying..')
                await asyncio.sleep(1)

