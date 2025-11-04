from typing import Union
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from oracle import OracleApp

oracle_app = OracleApp.get_singleton_instance()

app = FastAPI()

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

app.mount("/demo", StaticFiles(directory="public_demo", html=True), name="demo")

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

@app.get("/api/v0/test_only/dummy_outcome_for_event/{event_id}")
def dummy_outcome_for_event(event_id: str):
    return oracle_app.oracle.dummy_outcome_for_event(event_id)

@app.get("/")
def read_root():
    return {"Oracle": "API"}

