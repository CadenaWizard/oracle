// Copyright (c) 2025-present Cadena Bitcoin
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

use crate::crypto::{aggregate_secret_values, schnorrsig_compute_sig_point, schnorrsig_decompose};

use bitcoin::hashes::{sha256, sha256t_hash_newtype, Hash};
use bitcoin::hex::FromHex;
use bitcoin::key::{Keypair, Secp256k1};
use bitcoin::secp256k1::{Message, PublicKey, SecretKey, XOnlyPublicKey};
use core::ptr;
use secp256k1_sys::{
    types::{c_int, c_uchar, c_void, size_t},
    CPtr, SchnorrSigExtraParams,
};
use secp256k1_zkp::schnorr::Signature as SchnorrSignature;
use secp256k1_zkp::EcdsaAdaptorSignature;
use secp256k1_zkp::Signing;

pub fn main_usecase() {
    println!("DLC Playground - Main usecase");

    // First the Oracle has to be known, with its public key

    let oracle_keypair = keypair_from_sec_key_hex(DUMMY_SECKEY_3).unwrap();
    let oracle_pubkey = oracle_keypair.x_only_public_key().0;
    println!("Oracle public key: {}", oracle_pubkey.to_string());

    // Then we need to know about the upcoming event, the possible outcomes (options)
    //.and for each outcome, an exact string to be used, and a nonce to be used in the signature from the oracle.
    // This info is owned by the oracle.

    // Outcome string(s): (we use here only one which will be used by the outcome)
    let option_3_string = "outcome003".to_string();
    let option_3_string_hash = sha256::Hash::hash(option_3_string.as_bytes()).to_byte_array();
    let option_3_string_msg = Message::from_digest(option_3_string_hash);
    println!("Outcome 3 string: '{}'", option_3_string);

    // Nonce published by the oracle
    let oracle_nonce_seckey_data = <[u8; 32]>::from_hex(DUMMY_NONCE_3).unwrap();
    let oracle_secp = Secp256k1::new();
    let oracle_nonce_pubkey = Keypair::from_seckey_slice(&oracle_secp, &oracle_nonce_seckey_data)
        .unwrap()
        .x_only_public_key()
        .0;
    println!("Nonce from the oracle: {}", oracle_nonce_pubkey.to_string());

    // Next there are the two counterparties, we call them clients.
    // They need to know each other (their public keys), agree on the oracle, on the event,
    // contributions, payouts, timeouts.

    // Create keys for the two clients
    let cli1_keypair = keypair_from_sec_key_hex(DUMMY_SECKEY_1).unwrap();
    let cli2_keypair = keypair_from_sec_key_hex(DUMMY_SECKEY_2).unwrap();
    println!(
        "Client 1 pubkey: {}",
        cli1_keypair.x_only_public_key().0.to_string()
    );
    println!(
        "Client 2 pubkey: {}",
        cli2_keypair.x_only_public_key().0.to_string()
    );

    // Then they can create a funding transaction, here we just sign it by client1
    // Create signature for the funding transaction
    let funding_tx_sighash = Message::from_digest(<[u8; 32]>::from_hex(DUMMY_SIGHASH_1).unwrap());
    // Signature of cli1 on the funding transaction
    let cli1_secp = Secp256k1::new();
    let funding_tx_sig_cli1 =
        cli1_secp.sign_schnorr_no_aux_rand(&funding_tx_sighash, &cli1_keypair);
    // verify the signature
    let _res = cli1_secp
        .verify_schnorr(
            &funding_tx_sig_cli1,
            &funding_tx_sighash,
            &cli1_keypair.x_only_public_key().0,
        )
        .unwrap();

    // Next they create a Contract Execution Transaction (CET) for each possible outcome.
    // The CET spends the funding transaction, and it is not presigned by both clients.
    // Here comes the trick: a client creates an adaptor signature for a CET, and gives this to the other client.
    // The adaptor signature in itself is not suitable for signing the CET, only after the outcome from the oracle (attestation).

    // Client2 creates an adaptor signature for the option
    // Get the adaptor point (signature point)
    let cli2_secp = Secp256k1::new();
    let adaptor_point_3: PublicKey = schnorrsig_compute_sig_point(
        &cli2_secp,
        &oracle_pubkey,
        &oracle_nonce_pubkey,
        &option_3_string_msg,
    )
    .unwrap();
    assert_eq!(
        adaptor_point_3.to_string(),
        "0370981f036b26f7dde0b5dd6de2640f7166d12e10799077b552057aae483b9dda"
    );

    let cet_3_tx_sighash_msg = Message::from_digest(<[u8; 32]>::from_hex(DUMMY_SIGHASH_2).unwrap());
    // Creates adaptor signature
    #[cfg(feature = "std")]
    let adaptor_signature_3 = EcdsaAdaptorSignature::encrypt(
        &cli2_secp,
        &cet_3_tx_sighash_msg,
        &cli2_keypair.secret_key(),
        &adaptor_point_3,
    );
    // Adaptor signature is variable, can't assert it
    assert_eq!(adaptor_signature_3.to_string().len(), 324);
    println!("Adaptor signature: {}", adaptor_signature_3.to_string());

    // Verify the adaptor signature
    let _verif = adaptor_signature_3
        .verify(
            &cli2_secp,
            &cet_3_tx_sighash_msg,
            &cli2_keypair.public_key(),
            &adaptor_point_3,
        )
        .unwrap();

    // Then we wait and wait and wait for the outcome
    // Eventually the oracle has the outcome, and signs the outcome option, and published this signature
    println!("Waiting...");
    println!("The outcome is known now!");

    // The oracle signs the outcome
    let oracle_sig = schnorrsig_sign_with_nonce(
        &oracle_secp,
        &option_3_string_msg,
        &oracle_keypair,
        &oracle_nonce_seckey_data,
    );
    assert_eq!(oracle_sig.to_string(), "16447414e427df4c9c113939e45e029638662e3fef976b385e54bfb3b42d8de491364fb76aff8623fc9a61cbd06129aefeed11e136a74030e862ce819501ced5");
    println!("Oracle attestation signature: {}", oracle_sig.to_string());

    // Now the clients can sign their CET
    // Client1 signs the CET
    let (_nonce, s_value) = schnorrsig_decompose(&oracle_sig).unwrap();
    let adaptor_secret = SecretKey::from_slice(s_value).unwrap();
    assert_eq!(
        adaptor_secret.display_secret().to_string(),
        "91364fb76aff8623fc9a61cbd06129aefeed11e136a74030e862ce819501ced5"
    );
    let adapted_sig = adaptor_signature_3.decrypt(&adaptor_secret).unwrap();
    // Adapted signature is variable, can't assert
    assert!(adapted_sig.to_string().len() >= 140 && adapted_sig.to_string().len() <= 142);
    // The two signatures: the adapted signature is the signature of the other, we sign our own
    let other_sig = adapted_sig;
    let own_sig = cli1_secp.sign_ecdsa_low_r(&cet_3_tx_sighash_msg, &cli1_keypair.secret_key());
    assert_eq!(own_sig.to_string(), "30440220324bbb7c3fefb14d5d1fd8eb672b9ac5d95a8f021569df236f93d0a0763d805202201e926d2da413dc412bff9c583085260bd4a3dead09fc395a6f9ebdce259fedd9");
    assert_eq!(own_sig.to_string().len(), 140);
    println!(
        "Adapted signature of the counterparty: {}",
        other_sig.to_string()
    );
    println!(
        "Own signature:                         {}",
        own_sig.to_string()
    );

    // Verify the signatures
    // Verify our own signature
    let _res = cli1_secp
        .verify_ecdsa(&cet_3_tx_sighash_msg, &own_sig, &cli1_keypair.public_key())
        .unwrap();
    println!("Own signature verification OK");

    // And here comes the magic: the derived signature of the other party is also valid
    let _res = cli1_secp
        .verify_ecdsa(
            &cet_3_tx_sighash_msg,
            &other_sig,
            &cli2_keypair.public_key(),
        )
        .unwrap();
    println!("Other signature verification OK");

    // So at this point clients can execute the payout (braodcast the funding transaction and the CET)
}

fn string_to_message(s: &String) -> Message {
    let s_hash = sha256::Hash::hash(s.as_bytes()).to_byte_array();
    Message::from_digest(s_hash)
}

fn seckey_to_pubkey(sec: &[u8]) -> XOnlyPublicKey {
    let secp = Secp256k1::new();
    Keypair::from_seckey_slice(&secp, sec)
        .unwrap()
        .x_only_public_key()
        .0
}

pub fn usecase_with_digits() {
    let n = 3;
    println!("DLC Playground - Usecase with {} digits", n);

    // First the Oracle has to be known, with its public key

    let oracle_keypair = keypair_from_sec_key_hex(DUMMY_SECKEY_3).unwrap();
    let oracle_pubkey = oracle_keypair.x_only_public_key().0;
    println!("Oracle public key: {}", oracle_pubkey.to_string());

    // Then we need to know about the upcoming event, the possible outcomes (options)
    //.and for each outcome, an exact string to be used, and a nonce to be used in the signature from the oracle.
    // This info is owned by the oracle.

    // Outcome strings: one for each digit
    // Let's assume we deal with outcome "157", for which the combination of digits 1, 5, and 7 is used
    let digit_1_1_string = "event_666_digit_1_value_1".to_string();
    let digit_2_5_string = "event_666_digit_2_value_5".to_string();
    let digit_3_7_string = "event_666_digit_3_value_7".to_string();
    let digit_1_1_string_msg = string_to_message(&digit_1_1_string);
    let digit_2_5_string_msg = string_to_message(&digit_2_5_string);
    let digit_3_7_string_msg = string_to_message(&digit_3_7_string);
    println!(
        "Digit strings: '{}' '{}' '{}'",
        digit_1_1_string, digit_2_5_string, digit_3_7_string
    );

    // Nonces published by the oracle, one for each digit position
    let oracle_secp = Secp256k1::new();
    let oracle_nonce_1_seckey_data = <[u8; 32]>::from_hex(DUMMY_NONCE_1).unwrap();
    let oracle_nonce_2_seckey_data = <[u8; 32]>::from_hex(DUMMY_NONCE_2).unwrap();
    let oracle_nonce_3_seckey_data = <[u8; 32]>::from_hex(DUMMY_NONCE_3).unwrap();
    let oracle_nonce_1_pubkey = seckey_to_pubkey(&oracle_nonce_1_seckey_data);
    let oracle_nonce_2_pubkey = seckey_to_pubkey(&oracle_nonce_2_seckey_data);
    let oracle_nonce_3_pubkey = seckey_to_pubkey(&oracle_nonce_3_seckey_data);
    println!(
        "Nonces from the oracle: {} {} {}",
        oracle_nonce_1_pubkey.to_string(),
        oracle_nonce_2_pubkey.to_string(),
        oracle_nonce_3_pubkey.to_string(),
    );

    // Next there are the two counterparties, we call them clients.
    // They need to know each other (their public keys), agree on the oracle, on the event,
    // contributions, payouts, timeouts.

    // Create keys for the two clients
    let cli1_keypair = keypair_from_sec_key_hex(DUMMY_SECKEY_1).unwrap();
    let cli2_keypair = keypair_from_sec_key_hex(DUMMY_SECKEY_2).unwrap();
    println!(
        "Client 1 pubkey: {}",
        cli1_keypair.x_only_public_key().0.to_string()
    );
    println!(
        "Client 2 pubkey: {}",
        cli2_keypair.x_only_public_key().0.to_string()
    );

    // Then they can create a funding transaction, here we just sign it by client1
    // Create signature for the funding transaction
    let funding_tx_sighash = Message::from_digest(<[u8; 32]>::from_hex(DUMMY_SIGHASH_1).unwrap());
    // Signature of cli1 on the funding transaction
    let cli1_secp = Secp256k1::new();
    let funding_tx_sig_cli1 =
        cli1_secp.sign_schnorr_no_aux_rand(&funding_tx_sighash, &cli1_keypair);
    // verify the signature
    let _res = cli1_secp
        .verify_schnorr(
            &funding_tx_sig_cli1,
            &funding_tx_sighash,
            &cli1_keypair.x_only_public_key().0,
        )
        .unwrap();

    // Next they create a Contract Execution Transaction (CET) for each possible outcome.
    // The CET spends the funding transaction, and it is not presigned by both clients.
    // Here comes the trick: a client creates an adaptor signature for a CET, and gives this to the other client.
    // The adaptor signature in itself is not suitable for signing the CET, only after the outcome from the oracle (attestation).

    // Client2 creates an adaptor signatures for the outcome, one for each digit
    // Get the adaptor point (signature point)
    let cli2_secp = Secp256k1::new();
    let adaptor_point_1_1 = schnorrsig_compute_sig_point(
        &cli2_secp,
        &oracle_pubkey,
        &oracle_nonce_1_pubkey,
        &digit_1_1_string_msg,
    )
    .unwrap();
    let adaptor_point_2_5 = schnorrsig_compute_sig_point(
        &cli2_secp,
        &oracle_pubkey,
        &oracle_nonce_2_pubkey,
        &digit_2_5_string_msg,
    )
    .unwrap();
    let adaptor_point_3_7 = schnorrsig_compute_sig_point(
        &cli2_secp,
        &oracle_pubkey,
        &oracle_nonce_3_pubkey,
        &digit_3_7_string_msg,
    )
    .unwrap();
    // Aggregate the adaptor points
    let adaptor_point_aggregate_157 =
        PublicKey::combine_keys(&[&adaptor_point_1_1, &adaptor_point_2_5, &adaptor_point_3_7])
            .unwrap();
    // assert_eq!(
    //     adaptor_point_aggregate_157.to_string(),
    //     "0317ff483479ab2cd42c46e9493d6ba93ea9a036bd72b8fa0a298e8fddfdfa26ef"
    // );

    let cet_157_tx_sighash_msg =
        Message::from_digest(<[u8; 32]>::from_hex(DUMMY_SIGHASH_2).unwrap());
    // Creates adaptor signature
    #[cfg(feature = "std")]
    let adaptor_signature = EcdsaAdaptorSignature::encrypt(
        &cli2_secp,
        &cet_157_tx_sighash_msg,
        &cli2_keypair.secret_key(),
        &adaptor_point_aggregate_157,
    );
    // Adaptor signature is variable, can't assert it
    assert_eq!(adaptor_signature.to_string().len(), 324);
    println!("Adaptor signature: {}", adaptor_signature.to_string());

    // Then we wait and wait and wait for the outcome
    // Eventually the oracle has the outcome, and signs the outcome option, and published this signature
    println!("Waiting...");
    println!("The outcome is known now!");

    // The oracle signs the outcome digits
    let oracle_sig_1 = schnorrsig_sign_with_nonce(
        &oracle_secp,
        &digit_1_1_string_msg,
        &oracle_keypair,
        &oracle_nonce_1_seckey_data,
    );
    let oracle_sig_2 = schnorrsig_sign_with_nonce(
        &oracle_secp,
        &digit_2_5_string_msg,
        &oracle_keypair,
        &oracle_nonce_2_seckey_data,
    );
    let oracle_sig_3 = schnorrsig_sign_with_nonce(
        &oracle_secp,
        &digit_3_7_string_msg,
        &oracle_keypair,
        &oracle_nonce_3_seckey_data,
    );
    // assert_eq!(oracle_sig_3.to_string(), "16447414e427df4c9c113939e45e029638662e3fef976b385e54bfb3b42d8de48e52314735aa6fdb7175e8b13c6ec57e7af69ac5891803e2c49275b03d286845");
    println!(
        "Oracle attestation signatures:\n {}\n {}\n {}",
        oracle_sig_1.to_string(),
        oracle_sig_2.to_string(),
        oracle_sig_3.to_string()
    );

    // Now the clients can sign their CET
    // Client1 signs the CET
    let (_nonce, s_value_1) = schnorrsig_decompose(&oracle_sig_1).unwrap();
    let adaptor_secret_1 = SecretKey::from_slice(s_value_1).unwrap();
    let (_nonce, s_value_2) = schnorrsig_decompose(&oracle_sig_2).unwrap();
    let adaptor_secret_2 = SecretKey::from_slice(s_value_2).unwrap();
    let (_nonce, s_value_3) = schnorrsig_decompose(&oracle_sig_3).unwrap();
    let adaptor_secret_3 = SecretKey::from_slice(s_value_3).unwrap();
    // Aggregate the secrets
    let adaptor_secret_aggregate =
        aggregate_secret_values(&vec![adaptor_secret_1, adaptor_secret_2, adaptor_secret_3]);
    assert_eq!(
        adaptor_secret_aggregate.display_secret().to_string(),
        "8854d540cb4e75f70c358f657c016c288d6608c89b79a29649e7e9829521cd3a"
    );

    let adapted_sig = adaptor_signature
        .decrypt(&adaptor_secret_aggregate)
        .unwrap();
    // Adapted signature is variable, can't assert
    assert!(adapted_sig.to_string().len() >= 140 && adapted_sig.to_string().len() <= 142);
    // The two signatures: the adapted signature is the signature of the other, we sign our own
    let other_sig = adapted_sig;
    let own_sig = cli1_secp.sign_ecdsa_low_r(&cet_157_tx_sighash_msg, &cli1_keypair.secret_key());
    assert_eq!(own_sig.to_string(), "30440220324bbb7c3fefb14d5d1fd8eb672b9ac5d95a8f021569df236f93d0a0763d805202201e926d2da413dc412bff9c583085260bd4a3dead09fc395a6f9ebdce259fedd9");
    assert_eq!(own_sig.to_string().len(), 140);
    println!(
        "Adapted signature of the counterparty: {}",
        other_sig.to_string()
    );
    println!(
        "Own signature:                         {}",
        own_sig.to_string()
    );

    // Verify the signatures
    // Verify our own signature
    let _res = cli1_secp
        .verify_ecdsa(
            &cet_157_tx_sighash_msg,
            &own_sig,
            &cli1_keypair.public_key(),
        )
        .unwrap();
    println!("Own signature verification OK");

    // And here comes the magic: the derived signature of the other party is also valid
    let _res = cli1_secp
        .verify_ecdsa(
            &cet_157_tx_sighash_msg,
            &other_sig,
            &cli2_keypair.public_key(),
        )
        .unwrap();
    println!("Other signature verification OK");

    // So at this point clients can execute the payout (braodcast the funding transaction and the CET)
}

const DUMMY_SECKEY_1: &str = "1234000001000100000000000000000000000000000000000000000000004321";
const DUMMY_SECKEY_2: &str = "1234000001000200000000000000000000000000000000000000000000004321";
const DUMMY_SECKEY_3: &str = "1234000001000300000000000000000000000000000000000000000000004321";
const DUMMY_NONCE_1: &str = "1234000005000100000000000000000000000000000000000000000000004321";
const DUMMY_NONCE_2: &str = "1234000005000200000000000000000000000000000000000000000000004321";
const DUMMY_NONCE_3: &str = "1234000005000300000000000000000000000000000000000000000000004321";
const DUMMY_SIGHASH_1: &str = "1234000006000100000000000000000000000000000000000000000000004321";
const DUMMY_SIGHASH_2: &str = "1234000006000200000000000000000000000000000000000000000000004321";

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

extern "C" fn constant_nonce_fn(
    nonce32: *mut c_uchar,
    _msg32: *const c_uchar,
    _msg_len: size_t,
    _key32: *const c_uchar,
    _xonly_pk32: *const c_uchar,
    _algo16: *const c_uchar,
    _algo_len: size_t,
    data: *mut c_void,
) -> c_int {
    unsafe {
        ptr::copy_nonoverlapping(data as *const c_uchar, nonce32, 32);
    }
    1
}

/// Create a Schnorr signature using the provided nonce instead of generating one.
pub fn schnorrsig_sign_with_nonce<S: Signing>(
    secp: &Secp256k1<S>,
    msg: &Message,
    keypair: &Keypair,
    nonce: &[u8; 32],
) -> SchnorrSignature {
    unsafe {
        let mut sig = [0u8; secp256k1_zkp::constants::SCHNORR_SIGNATURE_SIZE];
        let extra_params =
            SchnorrSigExtraParams::new(Some(constant_nonce_fn), nonce.as_c_ptr() as *const c_void);
        assert_eq!(
            1,
            secp256k1_sys::secp256k1_schnorrsig_sign_custom(
                secp.ctx().as_ref(),
                sig.as_mut_c_ptr(),
                msg.as_c_ptr(),
                32_usize,
                keypair.as_c_ptr(),
                &extra_params,
            )
        );

        SchnorrSignature::from_slice(&sig).unwrap()
    }
}

fn keypair_from_sec_key_hex(seckeyslice: &str) -> Result<Keypair, Error> {
    let secbin =
        <[u8; 32]>::from_hex(&seckeyslice).map_err(|e| format!("Error in hex string {}", e))?;
    let secp = Secp256k1::new();
    let keypair = Keypair::from_seckey_slice(&secp, &secbin)
        .map_err(|e| format!("Error in secret key processing {}", e))?;
    Ok(keypair)
}

#[cfg(test)]
mod tests {
    use super::*;

    const DUMMY_MSGDIG_1: &str = "1234000004000100000000000000000000000000000000000000000000004321";

    #[test]
    fn test_sign() {
        let dummy_keypair = keypair_from_sec_key_hex(DUMMY_SECKEY_1).unwrap();
        let msg_digest = Message::from_digest(<[u8; 32]>::from_hex(DUMMY_MSGDIG_1).unwrap());
        let secp = Secp256k1::new();
        let sig = secp.sign_schnorr_no_aux_rand(&msg_digest, &dummy_keypair);
        assert_eq!(sig.to_string(), "90e0eae068c05e25c9e241476563adf4977ff579208daa689c35e7606a59940047349dca23889ca0d4aec1d561e7a723e02b7a29a07f2b8ab85d0a65f61d901d");
    }

    #[test]
    fn test_verify() {
        let dummy_keypair = keypair_from_sec_key_hex(DUMMY_SECKEY_1).unwrap();
        let (dummy_pubkey, _parity) = XOnlyPublicKey::from_keypair(&dummy_keypair);
        let msg_digest = Message::from_digest(<[u8; 32]>::from_hex(DUMMY_MSGDIG_1).unwrap());

        let secp = Secp256k1::new();
        let sig = secp.sign_schnorr_no_aux_rand(&msg_digest, &dummy_keypair);

        let _res = secp
            .verify_schnorr(&sig, &msg_digest, &dummy_pubkey)
            .unwrap();
    }

    #[test]
    fn test_signatures_full_usecase() {
        main_usecase();
    }

    #[test]
    fn test_signatures_usecase_with_digits() {
        usecase_with_digits();
    }
}

// TO check create_cet_adaptor_sig_is_valid
