# Copyright (c) 2025-present Cadena Bitcoin
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import dlccryptlib_oracle

xpub = dlccryptlib_oracle.init('sample_secret.sec', 'password')
print('Library initialized, xpub', xpub)

xpub = dlccryptlib_oracle.get_xpub()
print('Xpub', xpub)
pubkey0 = dlccryptlib_oracle.get_public_key(0)
print('Pubkey 0', pubkey0)
address0 = dlccryptlib_oracle.get_address(0)
print('Address 0', address0)

event_id = "event001"
nonce0_arr = dlccryptlib_oracle.create_deterministic_nonce(event_id, 0)
nonce0_pub = nonce0_arr[1]
print('Nonce 0 (pub)', nonce0_pub)
nonce1_arr = dlccryptlib_oracle.create_deterministic_nonce(event_id, 1)
nonce1_sec = nonce1_arr[0]
nonce1_pub = nonce1_arr[1]
print('Nonce 1 (pub, sec)', nonce1_pub, nonce1_sec)
nonce2_arr = dlccryptlib_oracle.create_deterministic_nonce(event_id, 2)

# Sign the event id with nonce1
sig = dlccryptlib_oracle.sign_schnorr_with_nonce(event_id, nonce1_sec, 0)
print('Signature:  ', sig)

# Sign again (same nonce)
print('Sign again: ', dlccryptlib_oracle.sign_schnorr_with_nonce(event_id, nonce1_sec, 0))

# Sign with different nonce
print('Sign with other nonce: ', dlccryptlib_oracle.sign_schnorr_with_nonce(event_id, nonce2_arr[0], 0))
