from db import db_setup
from db_infra import get_db_file, get_db_update_versions_from_args, print_current_db_version

import sqlite3
import sys


[vto, vfrom] = get_db_update_versions_from_args(1)
dbfile = get_db_file(db_file_name="ora.db", data_dir=".", create_mode=(vfrom==0))

print_current_db_version(dbfile)

print(f"Create/Update DB v{vfrom} -> v{vto} '{dbfile}'. Press Y to continue")
input = input()
if input.upper() != "Y":
    print(f"Aborting")
    sys.exit(1)

# Connect to SQLite database
conn = sqlite3.connect(dbfile)
# Explicitely enable Foreign Key support!
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys = TRUE")
cursor.close()
db_setup(conn)
conn.close()

print_current_db_version(dbfile)
print(f"DB created/updated.  Check location!  {dbfile}")

