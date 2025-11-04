// Copyright (c) 2025-present Cadena Bitcoin
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

use bitcoin::hashes::{sha256, sha256t_hash_newtype, Hash};
use bitcoin::key::Secp256k1;
use bitcoin::secp256k1::{Message, PublicKey, SecretKey, XOnlyPublicKey};
use secp256k1_zkp::schnorr::Signature as SchnorrSignature;
use secp256k1_zkp::Scalar;
use secp256k1_zkp::Verification;

pub type Error = String;

const BIP340_MIDSTATE: [u8; 32] = [
    0x9c, 0xec, 0xba, 0x11, 0x23, 0x92, 0x53, 0x81, 0x11, 0x67, 0x91, 0x12, 0xd1, 0x62, 0x7e, 0x0f,
    0x97, 0xc8, 0x75, 0x50, 0x00, 0x3c, 0xc7, 0x65, 0x90, 0xf6, 0x11, 0x64, 0x33, 0xe9, 0xb6, 0x6a,
];

sha256t_hash_newtype! {
    /// BIP340 Hash Tag
    pub struct BIP340HashTag = raw(BIP340_MIDSTATE, 64);

    /// BIP340 Hash
    #[hash_newtype(backward)]
    pub struct BIP340Hash(_);
}

fn create_schnorr_hash(msg: &Message, nonce: &XOnlyPublicKey, pubkey: &XOnlyPublicKey) -> [u8; 32] {
    let mut buf = Vec::<u8>::new();
    buf.extend(nonce.serialize());
    buf.extend(pubkey.serialize());
    buf.extend(msg.as_ref().to_vec());
    BIP340Hash::hash(&buf).to_byte_array()
}

fn schnorr_pubkey_to_pubkey(schnorr_pubkey: &XOnlyPublicKey) -> Result<PublicKey, Error> {
    let mut buf = Vec::<u8>::with_capacity(33);
    buf.push(0x02);
    buf.extend(schnorr_pubkey.serialize());
    Ok(PublicKey::from_slice(&buf).map_err(|e| e.to_string())?)
}

/// Compute a signature point for the given public key, nonce and message.
pub fn schnorrsig_compute_sig_point<C: Verification>(
    secp: &Secp256k1<C>,
    pubkey: &XOnlyPublicKey,
    nonce: &XOnlyPublicKey,
    message: &Message,
) -> Result<PublicKey, Error> {
    let hash = create_schnorr_hash(message, nonce, pubkey);
    let pk = schnorr_pubkey_to_pubkey(pubkey)?;
    let scalar = Scalar::from_be_bytes(hash).unwrap();
    let tweaked = pk.mul_tweak(secp, &scalar).map_err(|e| e.to_string())?;
    let npk = schnorr_pubkey_to_pubkey(nonce)?;
    Ok(npk.combine(&tweaked).map_err(|e| e.to_string())?)
}

pub fn message_hash(msg: &str) -> Result<Message, String> {
    Message::from_digest_slice(sha256::Hash::hash(msg.as_bytes()).as_byte_array())
        .map_err(|e| e.to_string())
}

/*
pub fn message_from_hex(message_hex: &str) -> Result<Message, String> {
    let pubbin = <[u8; 32]>::from_hex(&message_hex)
        .map_err(|e| format!("Error in hex string {} ({})", e, message_hex))?;
    let message = Message::from_digest_slice(&pubbin)
        .map_err(|e| format!("Error in message processing {}", e))?;
    Ok(message)
}
*/

/// Decompose a bip340 signature into a nonce and a secret key (as byte array)
pub fn schnorrsig_decompose(
    signature: &SchnorrSignature,
) -> Result<(XOnlyPublicKey, &[u8]), Error> {
    let bytes = signature.as_ref();
    Ok((
        XOnlyPublicKey::from_slice(&bytes[0..32]).map_err(|e| e.to_string())?,
        &bytes[32..64],
    ))
}

pub fn aggregate_secret_values(secrets: &Vec<SecretKey>) -> SecretKey {
    if secrets.len() == 0 {
        panic!("At least one key is required!");
    }
    let secret = secrets[0];
    let result = secrets.iter().skip(1).fold(secret, |accum, s| {
        accum.add_tweak(&Scalar::from(*s)).unwrap()
    });
    result
}
