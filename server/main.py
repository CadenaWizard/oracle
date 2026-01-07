# Copyright (c) 2025-present Cadena Bitcoin
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from oracle import OracleApp

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

load_dotenv()
# Read debug mode from .env
debug_mode_env = os.getenv("DEMO_MODE", "")
demo_mode = False
if debug_mode_env == "1":
    demo_mode = True
    print("Debug mode enabled")

oracle_app = OracleApp.get_singleton_instance()

if demo_mode:
    app = FastAPI()
else:
    # disable API doc
    app = FastAPI(openapi_url=None)

# Specify your allowed origins here
allowed_origins = ["*"] # allow any origin, disable CORS
# allowed_origins = ["https://staging.purabitcoin.com", "https://purabitcoin.com", "http://localhost:3000", "http://localhost:8000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    #expose_headers=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

@app.get("/api/v0/oracle/oracle_info")
def api_oracle_info():
    return oracle_app.oracle.get_oracle_info()

@app.get("/api/v0/oracle/oracle_status")
def api_oracle_status():
    return oracle_app.oracle.get_oracle_status()

@app.get("/api/v0/event/event/{event_id}")
def api_event(event_id: str):
    return oracle_app.oracle.get_event_by_id(event_id)

@app.get("/api/v0/event/events")
def api_events(start_time: int = 0, end_time: int = 0, definition: str = None):
    return oracle_app.oracle.get_events_filter(start_time, end_time, definition)

@app.get("/api/v0/event/event_ids")
def api_event_ids(start_time: int = 0, end_time: int = 0, definition: str = None):
    return oracle_app.oracle.get_event_ids_filter(start_time, end_time, definition)

@app.get("/api/v0/event/event_classes")
def api_events():
    return oracle_app.oracle.get_event_classes()

@app.get("/api/v0/event/next_event")
def api_next_event(definition: str, period: float = 60):
    return oracle_app.oracle.get_next_event(definition, int(period))

@app.get("/api/v0/price/current_all")
def api_price_current_all():
    return oracle_app.get_current_prices()

@app.get("/api/v0/price/current/{symbol}")
def api_price_current(symbol: str):
    return oracle_app.get_current_price(symbol)

@app.get("/api/v0/price_info/current_all")
def api_price_current_all():
    return oracle_app.get_current_price_infos()

@app.get("/api/v0/price_info/current/{symbol}")
def api_price_current(symbol: str):
    return oracle_app.get_current_price_info(symbol)

if not demo_mode:
    # Disable demo page
    @app.get("/demo")
    def read_root():
        raise HTTPException(status_code=404, detail="Not demo mode")

app.mount("/", StaticFiles(directory="public", html=True), name="root")

