// Copyright (c) 2025-present Cadena Bitcoin
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

use dlccryptlib;

// Conditional compilation to exclude PyO3-related code for Android
#[cfg(feature = "with-pyo3")]
use pyo3::prelude::*;
#[cfg(feature = "with-pyo3")]
use pyo3::exceptions::PyException;
#[cfg(feature = "with-pyo3")]
use pyo3::wrap_pyfunction;


// ##### Facade functions for easy Python invocations (pyo3/maturin)

/// Initialize the library, load secret from encrypted file. Return the XPUB.
#[cfg(feature = "with-pyo3")]
#[pyfunction]
pub fn init(path_for_secret_file: String, encryption_password: String) -> PyResult<String> {
    dlccryptlib::init_intern(&path_for_secret_file, &encryption_password, false)
        .map_err(|e| PyErr::new::<PyException, _>(e))
}

#[cfg(feature = "with-pyo3")]
#[pyfunction]
pub fn reinit_for_testing(
    path_for_secret_file: String,
    encryption_password: String,
) -> PyResult<String> {
    dlccryptlib::init_intern(&path_for_secret_file, &encryption_password, true)
        .map_err(|e| PyErr::new::<PyException, _>(e))
}

/// network: "bitcoin", or "signet".
// #[cfg(test)]
#[cfg(feature = "with-pyo3")]
#[pyfunction]
pub fn init_with_entropy(entropy: String, network: String) -> PyResult<String> {
    dlccryptlib::init_with_entropy_intern(&entropy, &network).map_err(|e| PyErr::new::<PyException, _>(e))
}

/// Return the XPUB
#[cfg(feature = "with-pyo3")]
#[pyfunction]
pub fn get_xpub() -> PyResult<String> {
    dlccryptlib::get_xpub_intern().map_err(|e| PyErr::new::<PyException, _>(e))
}

/// Return a child public key (specified by its index).
#[cfg(feature = "with-pyo3")]
#[pyfunction]
pub fn get_public_key(index: u32) -> PyResult<String> {
    dlccryptlib::get_public_key_intern(index).map_err(|e| PyErr::new::<PyException, _>(e))
}

/// Return a child address (specified by index).
#[cfg(feature = "with-pyo3")]
#[pyfunction]
pub fn get_address(index: u32) -> PyResult<String> {
    dlccryptlib::get_address_intern(index).map_err(|e| PyErr::new::<PyException, _>(e))
}

/// Verify a child public key.
#[cfg(feature = "with-pyo3")]
#[pyfunction]
pub fn verify_public_key(index: u32, pubkey: String) -> PyResult<bool> {
    dlccryptlib::verify_public_key_intern(index, &pubkey).map_err(|e| PyErr::new::<PyException, _>(e))
}

/// Sign a hash with a child private key (specified by index).
#[cfg(feature = "with-pyo3")]
#[pyfunction]
pub fn sign_hash_ecdsa(hash: String, signer_index: u32, signer_pubkey: String) -> PyResult<String> {
    dlccryptlib::sign_hash_ecdsa_intern(&hash, signer_index, &signer_pubkey)
        .map_err(|e| PyErr::new::<PyException, _>(e))
}

/// Create a nonce value deterministically
#[cfg(feature = "with-pyo3")]
#[pyfunction]
pub fn create_deterministic_nonce(
    event_id: String,
    nonce_index: u32,
) -> PyResult<(String, String)> {
    dlccryptlib::create_deterministic_nonce_intern(&event_id, nonce_index)
        .map_err(|e| PyErr::new::<PyException, _>(e))
}

/// Sign a message using Schnorr, with a nonce, using a child key
#[cfg(feature = "with-pyo3")]
#[pyfunction]
pub fn sign_schnorr_with_nonce(msg: String, nonce_sec_hex: String, index: u32) -> PyResult<String> {
    dlccryptlib::sign_schnorr_with_nonce_intern(&msg, &nonce_sec_hex, index)
        .map_err(|e| PyErr::new::<PyException, _>(e))
}

/// Combine a number of public keys into one
#[cfg(feature = "with-pyo3")]
#[pyfunction]
pub fn combine_pubkeys(keys_hex: String) -> PyResult<String> {
    dlccryptlib::combine_pubkeys_intern(&keys_hex).map_err(|e| PyErr::new::<PyException, _>(e))
}

/// Combine a number of secret keys into one.
/// Warning: Handle secret keys with caution!
#[cfg(feature = "with-pyo3")]
#[pyfunction]
pub fn combine_seckeys(keys_hex: String) -> PyResult<String> {
    dlccryptlib::combine_seckeys_intern(&keys_hex).map_err(|e| PyErr::new::<PyException, _>(e))
}

/// Create adaptor signatures for a number of CETs
#[cfg(feature = "with-pyo3")]
#[pyfunction]
pub fn create_cet_adaptor_sigs(
    num_digits: u8,
    num_cets: u64,
    digit_string_template: String,
    oracle_pubkey: String,
    signing_key_index: u32,
    signing_pubkey: String,
    nonces: String,
    interval_wildcards: String,
    sighashes: String,
) -> PyResult<String> {
    dlccryptlib::create_cet_adaptor_sigs_intern(
        num_digits,
        num_cets,
        &digit_string_template,
        &oracle_pubkey,
        signing_key_index,
        &signing_pubkey,
        &nonces,
        &interval_wildcards,
        &sighashes,
    )
    .map_err(|e| PyErr::new::<PyException, _>(e))
}

/// Verify adaptor signatures for a number of CETs
#[cfg(feature = "with-pyo3")]
#[pyfunction]
pub fn verify_cet_adaptor_sigs(
    num_digits: u8,
    num_cets: u64,
    digit_string_template: String,
    oracle_pubkey: String,
    signing_pubkey: String,
    nonces: String,
    interval_wildcards: String,
    sighashes: String,
    signatures: String,
) -> PyResult<bool> {
    dlccryptlib::verify_cet_adaptor_sigs_intern(
        num_digits,
        num_cets,
        &digit_string_template,
        &oracle_pubkey,
        &signing_pubkey,
        &nonces,
        &interval_wildcards,
        &sighashes,
        &signatures,
    )
    .map_err(|e| PyErr::new::<PyException, _>(e))
}

/// Perform final signing of a CET
#[cfg(feature = "with-pyo3")]
#[pyfunction]
pub fn create_final_cet_sigs(
    signing_key_index: u32,
    signing_pubkey: String,
    other_pubkey: String,
    num_digits: u8,
    oracle_signatures: String,
    cet_value_wildcard: String,
    cet_sighash: String,
    other_adaptor_signature: String,
) -> PyResult<String> {
    dlccryptlib::create_final_cet_sigs_intern(
        signing_key_index,
        &signing_pubkey,
        &other_pubkey,
        num_digits,
        &oracle_signatures,
        &cet_value_wildcard,
        &cet_sighash,
        &other_adaptor_signature,
    )
    .map_err(|e| PyErr::new::<PyException, _>(e))
}

#[cfg(feature = "with-pyo3")]
#[pymodule]
fn dlcplazacryptlib(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(init, m)?)?;
    m.add_function(wrap_pyfunction!(reinit_for_testing, m)?)?;
    m.add_function(wrap_pyfunction!(init_with_entropy, m)?)?;
    m.add_function(wrap_pyfunction!(get_xpub, m)?)?;
    m.add_function(wrap_pyfunction!(get_public_key, m)?)?;
    m.add_function(wrap_pyfunction!(get_address, m)?)?;
    m.add_function(wrap_pyfunction!(verify_public_key, m)?)?;
    m.add_function(wrap_pyfunction!(sign_hash_ecdsa, m)?)?;
    m.add_function(wrap_pyfunction!(create_deterministic_nonce, m)?)?;
    m.add_function(wrap_pyfunction!(sign_schnorr_with_nonce, m)?)?;
    m.add_function(wrap_pyfunction!(combine_pubkeys, m)?)?;
    m.add_function(wrap_pyfunction!(combine_seckeys, m)?)?;
    m.add_function(wrap_pyfunction!(create_cet_adaptor_sigs, m)?)?;
    m.add_function(wrap_pyfunction!(verify_cet_adaptor_sigs, m)?)?;
    m.add_function(wrap_pyfunction!(create_final_cet_sigs, m)?)?;
    Ok(())
}


