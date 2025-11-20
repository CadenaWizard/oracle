from oracle import Oracle
from datetime import datetime, UTC
import sys

def do_fill_db():
    pubkey = Oracle.initialize_cryptlib()
    o = Oracle(public_key=pubkey, data_dir=".")
    o.print_stats()
    print(f"\nOracle instance created\n")

    print(f"About to REINITIALIZE by generating default events. Press Y to continue")
    inputt = input()
    if inputt.upper() != "Y":
        print(f"Aborting")
        sys.exit(1)

    o.db.delete_all_contents()
    o.db.print_stats()
    now = round(datetime.now(UTC).timestamp())

    ec1 = o.create_event_class(class_id="btcusd", definition="BTCUSD", digits=7, digit_low_pos=0, repeat_period=10*60, repeat_offset=0, public_key=pubkey, now=now)
    ec2 = o.create_event_class(class_id="btceur", definition="BTCEUR", digits=7, digit_low_pos=0, repeat_period=12*3600, repeat_offset=0, public_key=pubkey, now=now)
    default_event_classes=[ec1, ec2]

    o.load_event_classes(default_event_classes, defer_nonces=False)
    o.print_stats()

    o.check_outcome_loop(early_exit=True)
    o.fill_nonces_all()
    o.check_outcome_loop(early_exit=True)

    o.print_stats()
    print(f"\nDone\n")

if __name__ == "__main__":
    do_fill_db()
