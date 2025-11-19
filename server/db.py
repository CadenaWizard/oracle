# Copyright (c) 2025-present Cadena Bitcoin
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from db_infra import get_db_file, print_current_db_version
from dto import DigitOutcome, EventClassDto, EventDto, Nonce, OutcomeDto

import sqlite3
import sys
import threading


LATEST_DB_VERSION = 1

# Upgrade from an older version, versions taken from args
def db_setup(conn: sqlite3.Connection):
    vto = LATEST_DB_VERSION
    vfrom = vto - 1
    if len(sys.argv) >= 3:
        vfrom = int(sys.argv[1])
        vto = int(sys.argv[2])
    db_setup_from_to(conn, vfrom, vto)


# Upgrade from an older version, versions have default values
def db_setup_from_to(conn: sqlite3.Connection, vfrom = 0, vto = LATEST_DB_VERSION):
    print(f"Updating DB from v{vfrom} to v{vto}")

    if vfrom <= 0 and vto >= 1:
        db_update_0_1(conn)


def db_update_0_1(conn: sqlite3.Connection):
    cursor = conn.cursor()

    cursor.execute("CREATE TABLE VERSION (Version INTEGER)")
    cursor.execute("INSERT INTO VERSION (Version) VALUES (1)")

    cursor.execute("""
        CREATE TABLE EVENTCLASS (
            Id VARCHAR(100) PRIMARY KEY,
            CreateTime INTEGER,
            Definition VARCHAR(100),
            RangeDigits INTEGER,
            RangeDigitsLowPos INTEGER,
            StringTemplate VARCHAR(100),
            RepeatFirstTime INTEGER,
            RepeatPeriod INTEGER,
            RepeatOffset INTEGER,
            RepeatLastTime INTEGER,
            SignerPublicKey VARCHAR(100)
        )
    """)
    cursor.execute("CREATE INDEX EcId ON EVENTCLASS (Id)")
    cursor.execute("CREATE INDEX EcDefinition ON EVENTCLASS (Definition)")

    cursor.execute("""
        CREATE TABLE PUBKEY (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Pubkey VARCHAR(100)
        )
    """)
    cursor.execute("CREATE INDEX PubkeyId ON PUBKEY (Id)")
    cursor.execute("CREATE INDEX PubkeyPubkey ON PUBKEY (Pubkey)")

    cursor.execute("""
        CREATE TABLE EVENT (
            EventId VARCHAR(100) PRIMARY KEY,
            ClassId VARCHAR(100),
            Definition VARCHAR(100),
            Time INTEGER,
            StringTemplate VARCHAR(100),
            PublicKeyId INTEGER,
            FOREIGN KEY (ClassId) REFERENCES EVENTCLASS(Id)
            FOREIGN KEY (PublicKeyId) REFERENCES PUBKEY(Id)
        )
    """)
    cursor.execute("CREATE INDEX EvEventId ON EVENT (EventId)")
    cursor.execute("CREATE INDEX EvClassId ON EVENT (ClassId)")
    cursor.execute("CREATE INDEX EvDefinition ON EVENT (Definition)")

    # TODO EventId should be a FOREIGN KEY
    cursor.execute("""
        CREATE TABLE NONCE (
            EventId VARCHAR(100),
            DigitIndex INTEGER,
            NoncePub VARCHAR(100),
            NonceSec VARCHAR(100)
        )
    """)
    cursor.execute("CREATE INDEX NonceEventId ON NONCE (EventId)")

    # TODO EventId should be a FOREIGN KEY
    cursor.execute("""
        CREATE TABLE DIGITOUTCOME (
            EventId VARCHAR(100),
            Idx INTEGER,
            Value INTEGER,
            Nonce VARCHAR(100),
            Signature VARCHAR(100),
            MsgStr VARCHAR(100)
        )
    """)
    cursor.execute("CREATE INDEX DOEventId ON DIGITOUTCOME (EventId)")

    # TODO EventId should be a FOREIGN KEY
    cursor.execute("""
        CREATE TABLE OUTCOME (
            EventId VARCHAR(100),
            Value INTEGER,
            CreatedTime INTEGER
        )
    """)
    cursor.execute("CREATE INDEX OutcEventId ON OUTCOME (EventId)")

    # Commit changes and close connection
    conn.commit()
    cursor.close()


def db_delete_all_contents(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM NONCE")
    cursor.execute("DELETE FROM DIGITOUTCOME")
    cursor.execute("DELETE FROM OUTCOME")
    cursor.execute("DELETE FROM EVENT")
    cursor.execute("DELETE FROM EVENTCLASS")
    cursor.execute("DELETE FROM PUBKEY")
    conn.commit()
    cursor.close()


def db_eventclass_insert_if_missing(cursor: sqlite3.Cursor, ec: EventClassDto) -> int:
    cursor.execute("SELECT Id FROM EVENTCLASS WHERE Id = ?", (ec.id,))
    rows = cursor.fetchall()
    if len(rows) >= 1:
        if len(rows[0]) >= 1:
            if rows[0][0] == ec.id:
                # already present
               return 0

    # Not found, insert
    cursor.execute(
        """
            INSERT INTO EVENTCLASS
            (
                Id, CreateTime, Definition, RangeDigits, RangeDigitsLowPos, StringTemplate,
                RepeatFirstTime, RepeatPeriod, RepeatOffset, RepeatLastTime, SignerPublicKey
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING Id
        """,
        (
            ec.id, ec.create_time, ec.definition, ec.range_digits, ec.range_digit_low_pos, ec.event_string_template,
            ec.repeat_first_time, ec.repeat_period, ec.repeat_offset, ec.repeat_last_time, ec.signer_public_key,
        )
    )
    rows = cursor.fetchall()
    if len(rows) >= 1:
        if len(rows[0]) >= 1:
            if rows[0][0] == ec.id:
                # Inserted OK
                return 1

    raise Exception(f"ERROR Could not insert event class {ec.id} {ec.definition}")


def _db_count_from_table(cursor: sqlite3.Cursor, table: str) -> int:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    rows = cursor.fetchall()
    if len(rows) >= 1:
        if len(rows[0]) >= 1:
            if rows[0][0] is not None:
                return int(rows[0][0])
    return -1


def db_eventclass_count(cursor: sqlite3.Cursor) -> int:
    return _db_count_from_table(cursor, "EVENTCLASS")


def _db_eventclass_from_row(r) -> EventClassDto | None:
    if len(r) < 11:
        return None
    return EventClassDto(
        r[0], int(r[1]), r[2], int(r[3]), int(r[4]), r[5],
        int(r[6]), int(r[7]), int(r[8]), int(r[9]), r[10]
    )

def db_eventclass_get_all(cursor: sqlite3.Cursor) -> list[EventClassDto]:
    cursor.execute("""
        SELECT
            Id, CreateTime, Definition, RangeDigits, RangeDigitsLowPos, StringTemplate,
            RepeatFirstTime, RepeatPeriod, RepeatOffset, RepeatLastTime, SignerPublicKey
        FROM EVENTCLASS
    """)
    ret = []
    rows = cursor.fetchall()
    for r in rows:
        ec = _db_eventclass_from_row(r)
        if ec is not None:
            ret.append(ec)
    return ret


def db_eventclass_get_by_id(cursor: sqlite3.Cursor, id: str) -> EventClassDto | None:
    cursor.execute("""
        SELECT
            Id, CreateTime, Definition, RangeDigits, RangeDigitsLowPos, StringTemplate,
            RepeatFirstTime, RepeatPeriod, RepeatOffset, RepeatLastTime, SignerPublicKey
        FROM EVENTCLASS
        WHERE Id == ?
    """, (id,))
    rows = cursor.fetchall()
    if len(rows) < 1:
        return None
    return _db_eventclass_from_row(rows[0])


def db_eventclass_latest_by_def(cursor: sqlite3.Cursor, defi: str) -> EventClassDto | None:
    cursor.execute("""
        SELECT
            Id, CreateTime, Definition, RangeDigits, RangeDigitsLowPos, StringTemplate,
            RepeatFirstTime, RepeatPeriod, RepeatOffset, RepeatLastTime, SignerPublicKey
        FROM EVENTCLASS
        WHERE Definition == ?
        ORDER BY CreateTime DESC
        LIMIT 1
    """, (defi,))
    rows = cursor.fetchall()
    if len(rows) < 1:
        return None
    return _db_eventclass_from_row(rows[0])


def db_eventclass_all_by_def(cursor: sqlite3.Cursor, defi: str) -> list[EventClassDto]:
    cursor.execute("""
        SELECT
            Id, CreateTime, Definition, RangeDigits, RangeDigitsLowPos, StringTemplate,
            RepeatFirstTime, RepeatPeriod, RepeatOffset, RepeatLastTime, SignerPublicKey
        FROM EVENTCLASS
        WHERE Definition == ?
    """, (defi,))
    ret = []
    rows = cursor.fetchall()
    for r in rows:
        ec = _db_eventclass_from_row(r)
        if ec is not None:
            ret.append(ec)
    return ret


# Insert if missing. Returns the pubkey id
def db_pubkey_insert_if_missing(cursor: sqlite3.Cursor, pubkey: str) -> int:
    cursor.execute("SELECT Id FROM PUBKEY WHERE Pubkey == ? LIMIT 1", (pubkey,))
    rows = cursor.fetchall()
    if len(rows) >= 1:
        if len(rows[0]) >= 1:
            if rows[0][0] is not None:
                return rows[0][0]
    # Not found, insert
    cursor.execute("INSERT INTO PUBKEY (Pubkey) Values (?) RETURNING Id", (pubkey,))
    rows = cursor.fetchall()
    if len(rows) >= 1:
        if len(rows[0]) >= 1:
            if rows[0][0] is not None:
                return rows[0][0]
    raise Exception(f"ERROR Could not insert public key {pubkey}")


def db_pubkey_count(cursor: sqlite3.Cursor) -> int:
    return _db_count_from_table(cursor, "PUBKEY")


def db_nonce_insert_one(cursor: sqlite3.Cursor, nonce: Nonce):
    cursor.execute("""
        INSERT INTO NONCE 
            (EventId, DigitIndex, NoncePub, NonceSec)
            VALUES (?, ?, ?, ?)
    """, (nonce.event_id, nonce.digit_index, nonce.nonce_pub, nonce.nonce_sec))
    # eventual error not checked


def db_nonce_get_all_by_id(cursor: sqlite3.Cursor, event_id: str) -> list[Nonce]:
    cursor.execute("""
        SELECT EventId, DigitIndex, NoncePub, NonceSec
        FROM NONCE
        WHERE EventId == ?
        ORDER BY DigitIndex ASC
    """, (event_id,))
    ret = []
    rows = cursor.fetchall()
    for r in rows:
        if len(r) >= 4:
            n = Nonce(r[0], int(r[1]), r[2], r[3])
            ret.append(n)
    return ret


def db_nonce_count(cursor: sqlite3.Cursor) -> int:
    return _db_count_from_table(cursor, "NONCE")


def db_digitoutcome_insert_list(cursor: sqlite3.Cursor, event_id: str, digit_outcome_list: list[DigitOutcome]):
    for do in digit_outcome_list:
        cursor.execute("""
            INSERT INTO DIGITOUTCOME
                (EventId, Idx, Value, Nonce, Signature, MsgStr)
                VALUES (?, ?, ?, ?, ?, ?)
        """, (event_id, do.index, int(do.value), do.nonce, do.signature, do.msg_str))
        # eventual error not checked


def db_digitoutcome_get_all_by_id(cursor: sqlite3.Cursor, event_id: str) -> list[DigitOutcome]:
    cursor.execute("""
        SELECT EventId, Idx, Value, Nonce, Signature, MsgStr
        FROM DIGITOUTCOME
        WHERE EventId == ?
        ORDER BY Idx ASC
    """, (event_id,))
    ret = []
    rows = cursor.fetchall()
    for r in rows:
        if len(r) >= 6:
            do = DigitOutcome(r[0], int(r[1]), int(r[2]), r[3], r[4], r[5])
            ret.append(do)
    return ret


def db_digitoutcome_count(cursor: sqlite3.Cursor) -> int:
    return _db_count_from_table(cursor, "DIGITOUTCOME")


def db_outcome_insert(cursor: sqlite3.Cursor, o: OutcomeDto):
    cursor.execute("""
        INSERT INTO OUTCOME
            (EventId, Value, CreatedTime)
            VALUES (?, ?, ?)
    """, (o.event_id, o.value, o.created_time))
    # eventual error not checked


def db_outcome_get_by_id(cursor: sqlite3.Cursor, event_id: str) -> OutcomeDto | None:
    cursor.execute("""
        SELECT EventId, Value, CreatedTime
        FROM OUTCOME
        WHERE EventId == ?
        LIMIT 1
    """, (event_id,))
    rows = cursor.fetchall()
    if len(rows) < 1:
        return None
    r = rows[0]
    if len(r) >= 3:
        return OutcomeDto(r[0], r[1], int(r[2]))
    return None


def db_outcome_exists(cursor: sqlite3.Cursor, event_id: str) -> bool:
    cursor.execute("SELECT COUNT(*) FROM OUTCOME WHERE EventId == ?", (event_id,))
    rows = cursor.fetchall()
    if len(rows) < 1:
        return False
    if len(rows[0]) < 1:
        return False
    if rows[0][0] is None:
        return False
    if int(rows[0][0]) < 1:
        return False
    return True


def db_outcome_count(cursor: sqlite3.Cursor) -> int:
    return _db_count_from_table(cursor, "OUTCOME")


def db_event_insert_if_missing(cursor: sqlite3.Cursor, e: EventDto) -> int:
    cursor.execute("SELECT EventId FROM EVENT WHERE EventId = ?", (e.event_id,))
    rows = cursor.fetchall()
    if len(rows) >= 1:
        if len(rows[0]) >= 1:
            if rows[0][0] == e.event_id:
                # already present
               return 0

    # Not found, insert
    cursor.execute(
        """
            INSERT INTO EVENT
            (EventId, ClassId, Definition, Time, StringTemplate, PublicKeyId)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING EventId
        """,
        (e.event_id, e.class_id, e.definition, e.time, e.string_template, e.signer_public_key_id)
    )
    rows = cursor.fetchall()
    if len(rows) >= 1:
        if len(rows[0]) >= 1:
            if rows[0][0] == e.event_id:
                # Inserted OK
                return 1

    raise Exception(f"ERROR Could not insert event {e.event_id} {e.class_id}")


def db_event_count(cursor: sqlite3.Cursor) -> int:
    return _db_count_from_table(cursor, "EVENT")


def _db_event_from_row(r) -> tuple[EventDto, str] | None:
    if len(r) < 7:
        return None
    e = EventDto(r[0], r[1], r[2], int(r[3]), r[4], int(r[6]))
    return [e, r[5]]


def db_event_get_by_id(cursor: sqlite3.Cursor, event_id: str) -> tuple[EventDto, str] | None:
    cursor.execute("""
        SELECT
            EVENT.EventId, EVENT.ClassId, EVENT.Definition, EVENT.Time, EVENT.StringTemplate, PUBKEY.Pubkey, PUBKEY.Id
        FROM EVENT
        LEFT OUTER JOIN PUBKEY ON PUBKEY.Id == EVENT.PublicKeyId
        WHERE EVENT.EventId == ?
    """, (event_id,))
    rows = cursor.fetchall()
    if len(rows) < 1:
        return None
    return _db_event_from_row(rows[0])


def db_event_get_earliest_time_without_outcome(cursor: sqlite3.Cursor) -> int:
    cursor.execute("""
        SELECT MIN(EVENT.Time)
        FROM EVENT
        LEFT OUTER JOIN OUTCOME ON EVENT.EventId == OUTCOME.EventId
        WHERE OUTCOME.EventId IS NULL
        ORDER BY EVENT.Time ASC
    """)
    rows = cursor.fetchall()
    print(rows)
    if len(rows) < 1:
        return 0
    if len(rows[0]) < 1:
        return 0
    if rows[0][0] is None:
        return 0
    return int(rows[0][0])


def db_event_get_past_no_outcome(cursor: sqlite3.Cursor, cutoff_time: int) -> list[str]:
    cursor.execute("""
        SELECT EVENT.EventId
        FROM EVENT
        LEFT OUTER JOIN OUTCOME ON EVENT.EventId == OUTCOME.EventId
        WHERE Time <= ?
        AND OUTCOME.EventId IS NULL
        ORDER BY EVENT.Time ASC
    """, (cutoff_time,))
    rows = cursor.fetchall()
    ret = []
    for r in rows:
        if len(r) >= 1:
            ret.append(r[0])
    return ret


def db_event_count_future(cursor: sqlite3.Cursor, cutoff_time: int) -> int:
    cursor.execute("""
        SELECT COUNT(*)
        FROM EVENT
        WHERE Time > ?
    """, (cutoff_time,))
    rows = cursor.fetchall()
    if len(rows) < 1:
        return -1
    if len(rows[0]) < 1:
        return -1
    if rows[0][0] is None:
        return 0
    return int(rows[0][0])


def _db_event_get_filter_where(cursor: sqlite3.Cursor, where_clause: str, params, limit: int) -> list[str]:
    query = "SELECT EventId FROM EVENT " + where_clause + " ORDER BY Time ASC"
    if limit == 0:
        cursor.execute(query, params)
    else:
        params = params + (limit,)
        cursor.execute(query + " LIMIT ?", params)
    rows = cursor.fetchall()
    ret = []
    for r in rows:
        if len(r) >= 1:
            ret.append(r[0])
    return ret


def db_event_get_filter_time_definition(cursor: sqlite3.Cursor, start_time: int, end_time: int, definition: str, limit: int) -> list[str]:
    params = ()
    if start_time != 0:
        if end_time != 0:
            if definition is not None:
                where_clause = "WHERE Time >= ? AND Time <= ? AND Definition == ?"
                params = (start_time, end_time, definition)
            else:
                where_clause = "WHERE Time >= ? AND Time <= ?"
                params = (start_time, end_time)
        else:
            if definition is not None:
                where_clause = "WHERE Time >= ? AND Definition == ?"
                params = (start_time, definition)
            else:
                where_clause = "WHERE Time >= ?"
                params = (start_time)
    else:
        if end_time != 0:
            if definition is not None:
                where_clause = "WHERE Time <= ? AND Definition == ?"
                params = (end_time, definition)
            else:
                where_clause = "WHERE Time <= ?"
                params = (end_time)
        else:
            if definition is not None:
                where_clause = "WHERE Definition == ?"
                params = (definition)
            else:
                where_clause = ""
                params = ()
    return _db_event_get_filter_where(cursor, where_clause, params, limit)


# Abstract persistence in DB. Takes care of connections.
# TODO Store publickeys separately
# TODO No on-demand Nonce creation, no deterministic nonces. Filled at creation, later used from DB
class EventStorageDb:
    def __init__(self, data_dir: str = "."):
        self.db_file_name = "ora.db"
        self.data_dir = data_dir
        # Cache connections, per each thread
        self._conn_ro = {}
        self._conn_rw = {}
        self._cursor_ro = {}
        dbfile = get_db_file(self.db_file_name, self.data_dir, create_mode=False)
        print_current_db_version(dbfile)

    def _open_ro(self) -> sqlite3.Connection:
        dbfile = get_db_file(self.db_file_name, self.data_dir, create_mode=False)
        dbfile_ro = "file:" + dbfile + "?mode=ro"
        conn = sqlite3.connect(dbfile_ro, uri=True)
        print("DB opened ro")
        return conn

    def _open_rw(self) -> sqlite3.Connection:
        dbfile = get_db_file(self.db_file_name, self.data_dir, create_mode=False)
        conn = sqlite3.connect(dbfile)
        print("DB opened rw")
        return conn

    def _getconn_ro(self):
        thid =  threading.current_thread().ident
        if thid in self._conn_ro:
            return self._conn_ro[thid]
        conn = self._open_ro()
        self._conn_ro[thid] = conn
        return conn

    # Take care of commit() as needed
    def _getconn_rw(self):
        thid =  threading.current_thread().ident
        if thid in self._conn_rw:
            return self._conn_rw[thid]
        conn = self._open_rw()
        self._conn_rw[thid] = conn
        return conn

    # Get cached RO cursor
    def _getcursor_ro(self):
        thid =  threading.current_thread().ident
        if thid in self._cursor_ro:
            return self._cursor_ro[thid]
        conn = self._getconn_ro()
        cursor = conn.cursor()
        self._cursor_ro[thid] = cursor
        return cursor

    def close(self):
        print("Closing DB ...")
        # TODO close all
        for _t, cur in self._cursor_ro.items():
            if cur is not None:
                cur.close()
        self._cursor_ro = {}
        for _t, c in self._conn_ro.items():
            if c is not None:
                c.close()
        self._conn_ro = {}
        for _t, c in self._conn_rw.items():
            if c is not None:
                c.close()
        self._conn_rw = {}
        print("DB closed")

    def delete_all_contents(self):
        print(f"WARNING: DB: deleting all contents!")
        db_delete_all_contents(self._getconn_rw())

    def print_stats(self):
        cursor = self._getcursor_ro()
        c_evcl = db_eventclass_count(cursor)
        c_pkey = db_pubkey_count(cursor)
        c_ev = db_event_count(cursor)
        c_nonce = db_nonce_count(cursor)
        c_diou = db_digitoutcome_count(cursor)
        c_outcome = db_outcome_count(cursor)
        print(f"DB stats: evcl: {c_evcl}  pkey: {c_pkey}  nonce: {c_nonce}  ev: {c_ev}  diou: {c_diou}  outcome: {c_outcome}")

    def event_classes_insert_if_missing(self, ec: EventClassDto) -> int:
        conn = self._getconn_rw()
        cursor = conn.cursor()
        ret = db_eventclass_insert_if_missing(cursor, ec)
        conn.commit()
        cursor.close()
        return ret

    def event_classes_len(self) -> int:
        cursor = self._getcursor_ro()
        cnt = db_eventclass_count(cursor)
        return cnt

    def event_classes_get_all(self) -> list[EventClassDto]:
        cursor = self._getcursor_ro()
        ret = db_eventclass_get_all(cursor)
        return ret

    # By (internal) ID, should be unique
    def event_classes_get_by_id(self, id: str) -> EventClassDto:
        cursor = self._getcursor_ro()
        return db_eventclass_get_by_id(cursor, id)

    # By definition. In case there are multiple, return latest (with highest create_time)
    def event_classes_get_latest_by_def(self, definition: str) -> EventClassDto:
        cursor = self._getcursor_ro()
        return db_eventclass_latest_by_def(cursor, definition)

    # By definition. In case there are multiple, return all
    def event_classes_get_all_by_def(self, definition: str) -> list[EventClassDto]:
        cursor = self._getcursor_ro()
        return db_eventclass_all_by_def(cursor, definition)

    # Also commits
    def nonces_insert_one(self, nonce: Nonce):
        conn = self._getconn_rw()
        cursor = conn.cursor()
        db_nonce_insert_one(cursor, nonce)
        conn.commit()
        cursor.close()

    def nonces_insert(self, nonces: list[Nonce]):
        conn = self._getconn_rw()
        cursor = conn.cursor()
        for n in nonces:
            db_nonce_insert_one(cursor, n)
        conn.commit()
        cursor.close()

    def nonces_get(self, event_id: str) -> list[Nonce]:
        cursor = self._getcursor_ro()
        return db_nonce_get_all_by_id(cursor, event_id)

    def events_insert_if_missing(self, e: EventDto, signer_public_key: str) -> int:
        conn = self._getconn_rw()
        cursor = conn.cursor()
        pubkey_id = db_pubkey_insert_if_missing(cursor, signer_public_key)
        e.signer_public_key_id = pubkey_id
        ret = db_event_insert_if_missing(cursor, e)
        conn.commit()
        cursor.close()
        return ret

    def events_append_if_missing(self, more_events: dict[str, EventDto], signer_public_key: str) -> int:
        conn = self._getconn_rw()
        cursor = conn.cursor()
        pubkey_id = db_pubkey_insert_if_missing(cursor, signer_public_key)
        added_cnt = 0
        for [_eid, e] in more_events.items():
            e.signer_public_key_id = pubkey_id
            added_cnt += db_event_insert_if_missing(cursor, e)
        conn.commit()
        cursor.close()
        return added_cnt

    def events_len(self) -> int:
        cursor = self._getcursor_ro()
        return db_event_count(cursor)

    # Also returns the signer pubkey
    def events_get_by_id(self, event_id: str) -> tuple[EventDto, str] | None:
        cursor = self._getcursor_ro()
        return db_event_get_by_id(cursor, event_id)

    # Get the time of the earliest event without outcome
    def events_get_earliest_time_without_outcome(self) -> int:
        cursor = self._getcursor_ro()
        return db_event_get_earliest_time_without_outcome(cursor)

    # Get (the ID of) events in the past with no outcome
    def events_get_past_no_outcome(self, now) -> list[str]:
        cursor = self._getcursor_ro()
        return db_event_get_past_no_outcome(cursor, now)

    """Count the number of future events"""
    def events_count_future(self, current_time: int):
        cursor = self._getcursor_ro()
        return db_event_count_future(cursor, current_time)

    def events_get_ids_filter(self, start_time: int, end_time: int, definition: str | None, limit: int) -> list[str]:
        cursor = self._getcursor_ro()
        return db_event_get_filter_time_definition(cursor, start_time, end_time, definition, limit)

    def digitoutcomes_insert(self, event_id: str, digit_outcome_list: list[DigitOutcome]):
        conn = self._getconn_rw()
        cursor = conn.cursor()
        db_digitoutcome_insert_list(cursor, event_id, digit_outcome_list)
        conn.commit()
        cursor.close()

    def digitoutcomes_get(self, event_id: str) -> list[DigitOutcome]:
        cursor = self._getcursor_ro()
        dos = db_digitoutcome_get_all_by_id(cursor, event_id)
        return dos

    def outcomes_get(self, event_id: str) -> OutcomeDto | None:
        cursor = self._getcursor_ro()
        return db_outcome_get_by_id(cursor, event_id)

    def outcomes_exists(self, event_id: str) -> bool:
        cursor = self._getcursor_ro()
        return db_outcome_exists(cursor, event_id)

    def outcomes_insert(self, o: OutcomeDto):
        conn = self._getconn_rw()
        cursor = conn.cursor()
        db_outcome_insert(cursor, o)
        conn.commit()
        cursor.close()


# Persistence in memory
# TODO Store publickeys separately
# TODO No on-demand Nonce creation, no deterministic nonces. Filled at creation, later used from DB
class EventStorage:
    def __init__(self):
        # Event classes, key is the event class id
        self._event_classes: dict[str, EventClassDto] = {}
        # Holds  nonces, key is event ID
        self._nonces: dict[str, list[Nonce]] = {}
        # Hold private keys separately (to save space)
        self._pubkeys: dict[int, str] = {}
        # Holds all the events, past and future. Key is the ID
        self._events: dict[str, EventDto] = {}
        # Holds digit outcomes, key is event ID
        self._digitoutcomes: dict[str, list[DigitOutcome]] = {}
        # Holds outcomes, key is event ID
        self._outcomes: dict[str, OutcomeDto] = {}


    def close(self):
        # do nothing
        return

    def delete_all_contents(self):
        print(f"WARNING: Storage: Deleting all contents!")
        self._event_classes = {}
        self._nonces = {}
        self._events = {}
        self._pubkeys = {}
        self._digitoutcomes = {}
        self._outcomes = {}

    def print_stats(self):
        print(f"DB stats: evcl: {len(self._event_classes)}  pkey {len(self._pubkeys)}  nonce: {len(self._nonces)}  ev: {len(self._events)}  diou: {len(self._digitoutcomes)}  outcome: {len(self._outcomes)}")

    def event_classes_insert_if_missing(self, ec: EventClassDto) -> int:
        ecid = ec.id
        if ecid in self._event_classes:
            # already present!
            return 0
        self._event_classes[ecid] = ec
        return 1

    def event_classes_len(self) -> int:
        return len(self._event_classes)

    def event_classes_get_all(self) -> list[EventClassDto]:
        return list(map(lambda entry: entry[1], self._event_classes.items()))

    # By (internal) ID, should be unique
    def event_classes_get_by_id(self, id: str) -> EventClassDto:
        if id in self._event_classes:
            return self._event_classes[id]
        # Not found
        return None

    # By definition. In case there are multiple, return latest (with highest create_time)
    def event_classes_get_latest_by_def(self, definition: str) -> EventClassDto:
        found = None
        latest_time = 0
        for _id, ec in self._event_classes.items():
            if ec.definition == definition:
                if ec.create_time > latest_time:
                    found = ec
                    latest_time = ec.create_time
        return found

    # By definition. In case there are multiple, return all
    def event_classes_get_all_by_def(self, definition: str) -> list[EventClassDto]:
        r = []
        for _id, ec in self._event_classes.items():
            if ec.definition == definition:
                r.append(ec)
        return r

    def nonces_insert_one(self, nonce: Nonce):
        eid = nonce.event_id
        if eid not in self._nonces:
            self._nonces[eid] = []
        self._nonces[eid].append(nonce)

    def nonces_insert(self, nonces: list[Nonce]):
        for n in nonces:
            self.nonces_insert_one(n)

    def nonces_get(self, event_id: str) -> list[Nonce]:
        if event_id not in self._nonces:
            return []
        return self._nonces[event_id]

    def pubkey_insert_if_missing(self, pubkey: str) -> int:
        for pid, p in self._pubkeys.items():
            if p == pubkey:
                return pid
        # Not found, add
        pid = len(self._pubkeys)
        assert(pid not in self._pubkeys)
        self._pubkeys[pid] = pubkey
        return pid

    def events_insert_if_missing(self, e: EventDto, signer_public_key: str) -> int:
        eid = e.event_id
        if eid in self._events:
            # Already present
            return 0
        pubkey_id = self.pubkey_insert_if_missing(signer_public_key)
        e.signer_public_key_id = pubkey_id
        self._events[eid] = e
        return 1

    def events_append_if_missing(self, more_events: dict[str, EventDto], signer_public_key: str) -> int:
        added_cnt = 0
        for [_eid, e] in more_events.items():
            added_cnt += self.events_insert_if_missing(e, signer_public_key)
        return added_cnt

    def events_len(self) -> int:
        return len(self._events)

    # Also returns the signer pubkey
    def events_get_by_id(self, event_id: str) -> tuple[EventDto, str] | None:
        if event_id not in self._events:
            return None
        e = self._events[event_id]
        if e.signer_public_key_id not in self._pubkeys:
            return None
        return [e, self._pubkeys[e.signer_public_key_id]]

    # Get the time of the earliest event without outcome
    def events_get_earliest_time_without_outcome(self) -> int:
        t = 0
        for eid, e in self._events.items():
            if self.outcomes_exists(eid):
                continue
            if t == 0:
                t = e.time
            else:
                if e.time < t:
                    t = e.time
        return t

    # Get (the ID of) events in the past with no outcome
    def events_get_past_no_outcome(self, now) -> list[str]:
        # past events without outcome
        pe = []
        for eid, e in self._events.items():
            if self.outcomes_exists(eid):
                continue
            if e.time > now:
                continue
            pe.append(e.event_id)
        return pe

    """Count the number of future events"""
    def events_count_future(self, current_time: int):
        c = 0
        for _eid, e in self._events.items():
            if e.time > current_time:
                c += 1
        return c

    def events_get_ids_filter(self, start_time: int, end_time: int, definition: str | None, limit: int) -> list[str]:
        events = []
        for _eid, e in self._events.items   ():
            if start_time != 0:
                if e.time < start_time:
                    continue
            if end_time != 0:
                if e.time > end_time:
                    continue
            if definition is not None:
                if e.definition != definition:
                    continue
            events.append(e)
            if len(events) >= limit:
                break
        # sort by time
        e_sorted = sorted(events, key=lambda e: e.time)
        return list(map(lambda e: e.event_id, e_sorted))

    def digitoutcomes_insert(self, event_id: str, digit_outcome_list: list[DigitOutcome]):
        self._digitoutcomes[event_id] = digit_outcome_list

    def digitoutcomes_get(self, event_id: str) -> list[DigitOutcome]:
        if event_id not in self._digitoutcomes:
            return []
        return self._digitoutcomes[event_id]

    def outcomes_get(self, event_id: str) -> OutcomeDto | None:
        if event_id in self._outcomes:
            return self._outcomes[event_id]
        return None

    def outcomes_exists(self, event_id: str) -> bool:
        if event_id in self._outcomes:
            return True
        return False

    def outcomes_insert(self, o: OutcomeDto):
        self._outcomes[o.event_id] = o
