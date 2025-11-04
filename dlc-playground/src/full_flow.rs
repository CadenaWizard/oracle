// Copyright (c) 2025-present Cadena Bitcoin
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

use crate::crypto::{
    aggregate_secret_values, message_hash, schnorrsig_compute_sig_point, schnorrsig_decompose,
};

use bitcoin::absolute::LockTime;
use bitcoin::blockdata::transaction::Transaction;
use bitcoin::consensus::Encodable;
use bitcoin::hashes::Hash;
use bitcoin::hex::{DisplayHex, FromHex};
use bitcoin::key::Secp256k1;
use bitcoin::opcodes::all::{OP_CHECKMULTISIG, OP_PUSHNUM_2};
use bitcoin::secp256k1::ecdsa::Signature;
use bitcoin::secp256k1::SecretKey;
use bitcoin::sighash::SighashCache;
use bitcoin::transaction::Version;
use bitcoin::{
    Address, Amount, CompressedPublicKey, EcdsaSighashType, KnownHrp, Network, OutPoint, PublicKey,
    ScriptBuf, TxIn, TxOut, Txid, Witness,
};
use secp256k1_zkp::schnorr::Signature as SchnorrSignature;
use secp256k1_zkp::{EcdsaAdaptorSignature, Message};
use serde::Deserialize;
use std::str::FromStr;
use std::time::{SystemTime, UNIX_EPOCH};

pub type Error = String;

#[derive(Clone, Debug)]
struct EventInfo {
    event_id: String,
    range_digits: u8,
    string_template: String,
    nonces: Vec<String>,
}

const PRICE_MIN: u64 = 75000;
const PRICE_MAX: u64 = 110000;

pub async fn full_use_case_main() {
    // Test secret keys
    let seckey_str_a = "0001020304050607080910111213141516171819202122232425262728293031";
    let seckey_str_b = "0001020304050607080910111213141516171819202122232425262728293037";

    // UTXOs used, specific to each run
    let utxos_a = vec![(
        "9f36ba8114f19746a7a544f4dd598d9a1cbee2184a87c6309b157d4ac07604a0",
        0,
        119705,
    )];
    let utxos_b = vec![(
        "9f36ba8114f19746a7a544f4dd598d9a1cbee2184a87c6309b157d4ac07604a0",
        1,
        106221,
    )];

    let fee_rate_per_kw = 12000;

    let oracle_api = "https://oracle.purabitcoin.com/api";
    let symbol = "BTCUSD";
    let duration_days: u32 = 30;
    let target_price = 150000;
    let network = bitcoin::Network::Signet;

    let secp_ctx = Secp256k1::new();
    let seckey_a = secret_key_from_hex(seckey_str_a);
    let seckey_b = secret_key_from_hex(seckey_str_b);
    let pubkey_a = PublicKey::from(seckey_a.public_key(&secp_ctx));
    let pubkey_b = PublicKey::from(seckey_b.public_key(&secp_ctx));
    let pubkey_a_str = pubkey_a.to_string();
    let pubkey_b_str = pubkey_b.to_string();
    println!("A pubkey: {}", pubkey_a_str);
    println!("B pubkey: {}", pubkey_b_str);

    // let a_payout_address =
    //     bitcoin::Address::p2wpkh(&dummy_compressed_pubkey(22, network), KnownHrp::Testnets)
    //         .to_string();
    // let b_payout_address =
    //     bitcoin::Address::p2wpkh(&dummy_compressed_pubkey(23, network), KnownHrp::Testnets)
    //         .to_string();
    let a_payout_address =
        bitcoin::Address::p2wpkh(&CompressedPublicKey(pubkey_a.inner), KnownHrp::Testnets);
    let b_payout_address =
        bitcoin::Address::p2wpkh(&CompressedPublicKey(pubkey_b.inner), KnownHrp::Testnets);
    println!("A payout address: {}", a_payout_address);
    println!("B payout address: {}", b_payout_address);

    let (oracle_pubkey_str, event_info) =
        obtain_suitable_event(oracle_api, symbol, duration_days).await;
    // println!("event id: {}", event_id);

    let oracle_pubkey = pubkey_from_hex(&oracle_pubkey_str).unwrap();
    println!("Oracle pubkey: {}", oracle_pubkey.to_string());

    let inputs_a = utxos_a
        .iter()
        .map(|(txid_str, vout, value)| {
            (
                TxIn {
                    previous_output: OutPoint {
                        txid: Txid::from_str(&txid_str).unwrap(),
                        vout: *vout,
                    },
                    ..Default::default()
                },
                *value,
            )
        })
        .collect();
    let inputs_b = utxos_b
        .iter()
        .map(|(txid_str, vout, value)| {
            (
                TxIn {
                    previous_output: OutPoint {
                        txid: Txid::from_str(&txid_str).unwrap(),
                        vout: *vout,
                    },
                    ..Default::default()
                },
                *value,
            )
        })
        .collect();
    let input_amount_a: u64 = utxos_a.iter().map(|(_id, _vout, value)| *value).sum();
    let input_amount_b: u64 = utxos_b.iter().map(|(_id, _vout, value)| *value).sum();
    // TODO contrib amount should be different, can be less than input amount
    let contrib_amount_a = input_amount_a;
    let contrib_amount_b = input_amount_b;

    // Create transactions on the server
    let mut dlc_txs = match create_transactions_server(
        // &oracle_api,
        // &oracle_pubkey,
        // symbol,
        // &event_info,
        target_price,
        &pubkey_a,
        &pubkey_b,
        &inputs_a,
        &inputs_b,
        contrib_amount_a,
        contrib_amount_b,
        &a_payout_address,
        &b_payout_address,
        network,
        fee_rate_per_kw,
    )
    // .await
    {
        Err(e) => panic!("{}", e),
        Ok(d) => d,
    };

    // Sign txs by client A
    let _res = sign_transactions_client(
        0,
        &seckey_a,
        &pubkey_a,
        &mut dlc_txs,
        &oracle_pubkey,
        &event_info,
    )
    .expect("Oops");

    // Sign txs by client B
    let _res = sign_transactions_client(
        1,
        &seckey_b,
        &pubkey_b,
        &mut dlc_txs,
        &oracle_pubkey,
        &event_info,
    )
    .expect("Oops");

    println!("Both clients signed!");

    println!(
        "Signed funding tx: {} {}",
        encode_tx_to_hex(&dlc_txs.funding_tx),
        dlc_txs.funding_tx.compute_txid(),
    );
    // println!("    {:?}", dlc_txs.funding_tx,);

    println!(
        "Signed refund tx: {} {}",
        encode_tx_to_hex(&dlc_txs.refund_tx),
        dlc_txs.refund_tx.compute_txid(),
    );
    // println!("    {:?}", dlc_txs.refund_tx,);

    // This is the outcome-time part, normally happens later
    println!();
    println!("Time for the OUTCOME!");
    println!();

    let event_outcome = obtain_oracle_outcome(oracle_api, &event_info.event_id).await;
    println!("Outcome obtained:");
    // println!("    {:?}", event_outcome);
    assert!(event_outcome.has_outcome);

    sign_final_cet(
        0,
        &seckey_a,
        &pubkey_a,
        // other's pubkey:
        &pubkey_b,
        &event_outcome,
        &mut dlc_txs,
    )
    .await
    .expect("Oops");
    // Also for other client
    sign_final_cet(
        1,
        &seckey_b,
        &pubkey_b,
        // other's pubkey:
        &pubkey_a,
        &event_outcome,
        &mut dlc_txs,
    )
    .await
    .expect("Oops");
}

fn secret_key_from_hex(sec_hex: &str) -> SecretKey {
    SecretKey::from_slice(&<[u8; 32]>::from_hex(sec_hex).unwrap()).unwrap()
}

/// Returns oracle pubkey and first suitable event id
async fn obtain_suitable_event(
    oracle_api: &str,
    symbol: &str,
    duration_days: u32,
) -> (String, EventInfo) {
    let oracle_pubkey = obtain_oracle_pubkey(oracle_api).await;
    println!("Oracle pubkey: {}", oracle_pubkey);

    let current_time = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    println!("current time {}", current_time);
    let outcome_time = current_time + duration_days as u64 * 86400;
    let event_info_dto = obtain_suitable_event_info(oracle_api, symbol, outcome_time).await;
    let event_info = EventInfo {
        event_id: event_info_dto.event_id,
        range_digits: event_info_dto.range_digits,
        string_template: event_info_dto.string_template,
        nonces: event_info_dto.nonces,
    };
    println!("event info: {:?}", event_info);
    println!("Suitable event ID: {}", event_info.event_id);

    (oracle_pubkey, event_info)
}

struct CetInfo {
    raw_val: u32,
    tx: Transaction,
    sighash: [u8; 32],
    adaptor_sig_a: Option<EcdsaAdaptorSignature>,
    adaptor_sig_b: Option<EcdsaAdaptorSignature>,
}

struct DlcTxs {
    funding_tx: Transaction,
    funding_inputs: Vec<(u8, TxIn, u64)>,
    funding_redeem_script: ScriptBuf,
    refund_tx: Transaction,
    cets: Vec<CetInfo>,
}

#[derive(Deserialize, Debug)]
struct OracleInfoDto {
    public_key: String,
}

async fn obtain_oracle_pubkey(oracle_api_url: &str) -> String {
    let request_url = oracle_api_url.to_owned() + "/v0/oracle/oracle_info";
    // println!("{}", request_url);

    let client = reqwest::Client::new();
    let response = client
        .get(request_url)
        // .header(USER_AGENT, "rust-web-api-client") // gh api requires a user-agent header
        .send()
        .await
        .expect("API error");

    let resp: OracleInfoDto = response.json().await.expect("API error");
    resp.public_key
}

#[derive(Clone, Deserialize, Debug)]
struct EventInfoDto {
    event_id: String,
    range_digits: u8,
    string_template: String,
    nonces: Vec<String>,
}

#[derive(Deserialize, Debug)]
struct EventInfosDto(Vec<EventInfoDto>);

#[derive(Clone, Deserialize, Debug)]
struct DigitOutcomeDto {
    // index: usize,
    // value: usize,
    // nonce: String,
    signature: String,
    // msg_str: String,
}

#[derive(Clone, Deserialize, Debug)]
struct EventWithOutcomeDto {
    outcome_value: f64,
    digits: Vec<DigitOutcomeDto>,
    has_outcome: bool,
}

async fn obtain_suitable_event_info(
    oracle_api: &str,
    symbol: &str,
    term_end_time: u64,
) -> EventInfoDto {
    let term_end_plus_2days = term_end_time + 2 * 86400;
    println!("times {} {}", term_end_time, term_end_plus_2days);
    let request_url = format!(
        "{}/v0/event/events?definition={}&start_time={}&end_time={}",
        oracle_api, symbol, term_end_time, term_end_plus_2days
    );
    // print(url)

    let client = reqwest::Client::new();
    let response = client
        .get(request_url)
        // .header(USER_AGENT, "rust-web-api-client") // gh api requires a user-agent header
        .send()
        .await
        .expect("API error");

    let resp: EventInfosDto = response.json().await.expect("API error");
    let first_event = resp.0[0].clone();
    first_event
}

fn pubkey_from_hex(pubkey_hex: &str) -> Result<PublicKey, String> {
    let pkbin =
        <[u8; 33]>::from_hex(&pubkey_hex).map_err(|e| format!("Error in hex string {}", e))?;
    let pubkey = PublicKey::from_slice(&pkbin)
        .map_err(|e| format!("Error in public key processing {}", e))?;
    Ok(pubkey)
}

fn multisig_redeem_script(key_a: &PublicKey, key_b: &PublicKey) -> ScriptBuf {
    let mut script = ScriptBuf::new();
    script.push_opcode(OP_PUSHNUM_2);
    script.push_slice(<[u8; 33]>::try_from(key_a.to_bytes().as_slice()).expect("Invalid length"));
    script.push_slice(<[u8; 33]>::try_from(key_b.to_bytes().as_slice()).expect("Invalid length"));
    script.push_opcode(OP_PUSHNUM_2);
    script.push_opcode(OP_CHECKMULTISIG);
    script
}

fn estimate_fee(fee_rate_per_kw: u32, estimated_vsize: u32, debug: bool) -> u64 {
    let fee = ((estimated_vsize as f64) / 1024f64 * (fee_rate_per_kw as f64)) as u64;
    if debug {
        println!("Fee (for {} vbytes): {}", estimated_vsize, fee);
    }
    fee
}

fn create_funding_transaction(
    pubkey_a: &PublicKey,
    pubkey_b: &PublicKey,
    inputs_a: &Vec<(TxIn, u64)>,
    inputs_b: &Vec<(TxIn, u64)>,
    contrib_amount_a: u64,
    contrib_amount_b: u64,
    network: Network,
    fee_rate_per_kw: u32,
) -> (Transaction, ScriptBuf) {
    println!("Creating funding transaction...");
    assert!(
        inputs_a.len() > 0 && inputs_b.len() > 0,
        "ERROR: Both parties must contribute at least one input"
    );
    let inputs = inputs_a
        .iter()
        .cloned()
        .chain(inputs_b.iter().cloned())
        .collect::<Vec<_>>();
    println!("{} inputs", inputs.len());
    for i in 0..inputs.len() {
        println!("    {} {:?}", i, inputs[i]);
    }
    let input_amount_a: u64 = inputs_a.iter().map(|(_txin, value)| *value).sum();
    let input_amount_b: u64 = inputs_b.iter().map(|(_txin, value)| *value).sum();
    // TODO use proper size estimate
    let estimated_weight = 300;
    let fee = estimate_fee(fee_rate_per_kw, estimated_weight, true);
    // TODO take into account contrib values, and create change if needed
    let funding_amount = input_amount_a + input_amount_b - fee;
    println!(
        "Contrib amounts: {} {}, inputs: {} {}, fee {}, Funding amount: {}",
        contrib_amount_a, contrib_amount_b, input_amount_a, input_amount_a, fee, funding_amount
    );
    let redeem_script = multisig_redeem_script(pubkey_a, pubkey_b);
    println!(
        "redeem script: {:?} {} {}",
        redeem_script,
        redeem_script.to_hex_string(),
        redeem_script
            .wscript_hash()
            .as_byte_array()
            .to_lower_hex_string()
    );
    // TODO add timelock
    let output_address = Address::p2wsh(redeem_script.as_script(), network);
    println!("Funding output address: {}", output_address);
    // TODO handle fees
    let output = TxOut {
        value: Amount::from_sat(funding_amount),
        script_pubkey: output_address.script_pubkey(),
    };
    let funding_transaction = Transaction {
        input: inputs.iter().map(|(txin, _)| txin.clone()).collect(),
        output: vec![output],
        version: Version::TWO,
        lock_time: LockTime::ZERO, // TODO
    };

    (funding_transaction, redeem_script)
}

fn encode_tx_to_hex(tx: &Transaction) -> String {
    let mut v = Vec::with_capacity(1024);
    match tx.consensus_encode(&mut v) {
        Err(e) => format!("Serialization error {}", e),
        Ok(_size) => v.to_lower_hex_string(),
    }
}

fn create_refund_transaction(
    payout_a_address: &Address,
    payout_b_address: &Address,
    funding_tx_id: &Txid,
    funding_tx_vout: u32,
    funding_tx_amount: u64,
    contrib_amount_a: u64,
    contrib_amount_b: u64,
    fee_rate_per_kw: u32,
    // network: Network,
) -> Transaction {
    println!("Creating refund transaction...");
    let funding_input = TxIn {
        previous_output: OutPoint::new(funding_tx_id.clone(), funding_tx_vout),
        ..Default::default()
    };

    // Compute refund amounts, from funding_amount, divided proportional to contributions
    // Note: will not be exactly the contribution, but less, due to fees.
    // TODO use proper size estimate
    let estimated_weight = 300;
    let fee = estimate_fee(fee_rate_per_kw, estimated_weight, true);
    let remain_amount = funding_tx_amount - fee;
    assert!(remain_amount > 0);
    let refund_amount_a = ((contrib_amount_a as f64
        / ((contrib_amount_a + contrib_amount_b) as f64))
        * remain_amount as f64) as u64;
    let refund_amount_b = remain_amount - refund_amount_a;

    let output_a = TxOut {
        value: Amount::from_sat(refund_amount_a),
        script_pubkey: payout_a_address.script_pubkey(),
    };
    let output_b = TxOut {
        value: Amount::from_sat(refund_amount_b),
        script_pubkey: payout_b_address.script_pubkey(),
    };
    // TODO add timelock
    let refund_tx = Transaction {
        input: vec![funding_input.clone()],
        output: vec![output_a, output_b],
        version: Version::TWO,
        lock_time: LockTime::ZERO,
    };

    refund_tx
}

fn create_digit_adaptor_sig_point(
    oracle_pubkey: &PublicKey,
    digit_index: u8,
    digit_outcome: u8,
    string_template: &str,
    nonce: &PublicKey,
) -> Result<secp256k1_zkp::PublicKey, String> {
    // print("Digit", digit_index, digit_outcome)
    let string_msg = string_template
        .to_string()
        .replace("{digit_index}", &digit_index.to_string())
        .replace("{digit_outcome}", &digit_outcome.to_string());
    // println!(
    //     "Digit outcome: idx {} outcome {} string {} nonce {}",
    //     digit_index,
    //     digit_outcome,
    //     string_msg,
    //     nonce.to_string()
    // );
    let msg_hash = message_hash(&string_msg)?;
    // print(msg_hash)
    let secp_ctx = Secp256k1::new();
    let sig_point = schnorrsig_compute_sig_point(
        &secp_ctx,
        &oracle_pubkey.inner.x_only_public_key().0,
        &nonce.inner.x_only_public_key().0,
        &msg_hash,
    )?;
    // print("    sig point", sig_point)
    Ok(sig_point)
}

fn value_to_digits(value: u32) -> Vec<u8> {
    let val_str = format!("{:0>7}", value);
    assert_eq!(val_str.len(), 7);
    val_str
        .chars()
        .map(|c| (c.to_ascii_lowercase() as u8 - 48) as u8)
        .collect::<Vec<u8>>()
}

fn combine_pubkeys(
    keys: &[&bitcoin::secp256k1::PublicKey],
) -> Result<bitcoin::secp256k1::PublicKey, String> {
    bitcoin::secp256k1::PublicKey::combine_keys(keys).map_err(|err| err.to_string())
}

fn payout_ratios_for_a_and_b(target_price: u64, outcome_price: u64) -> (f64, f64) {
    // TODO real payouts, not just simulated
    if outcome_price <= target_price {
        (1.0, 0.0)
    } else {
        (0.0, 1.0)
    }
}

fn payouts_for_a_and_b(target_price: u64, outcome_price: u64, full_amount: u64) -> (u64, u64) {
    let (ratio_a, _ratio_b) = payout_ratios_for_a_and_b(target_price, outcome_price);
    // TODO take into account platform fee
    let payout_a = (ratio_a * full_amount as f64) as u64;
    let payout_b = full_amount - payout_a;
    (payout_a, payout_b)
}

fn create_transactions_server(
    // oracle_api: &str,
    // oracle_pubkey: &PublicKey,
    // symbol: &str,
    // duration_days: u32,
    // event_info: &EventInfo,
    target_price: u64,
    pubkey_a: &PublicKey,
    pubkey_b: &PublicKey,
    inputs_a: &Vec<(TxIn, u64)>,
    inputs_b: &Vec<(TxIn, u64)>,
    // TODO: for inputs, separate input val and contrib val, TODO change output
    contrib_amount_a: u64,
    contrib_amount_b: u64,
    payout_a_address: &Address,
    payout_b_address: &Address,
    network: bitcoin::Network,
    fee_rate_per_kw: u32,
) -> Result<DlcTxs, Error> {
    println!("\nCreating transactions...\n");

    // println!("Symbol: {}", symbol);
    // println!("Duration: {} days", duration_days);
    // println!("Oracle pubkey: {}", oracle_pubkey.to_string());

    let current_time = SystemTime::now();
    println!(
        "Current time: {}",
        current_time.elapsed().unwrap_or_default().as_secs()
    );

    println!("A pubkey: {}", pubkey_a.to_string());
    println!("B pubkey: {}", pubkey_b.to_string());

    // Create funding transaction
    let (funding_transaction, funding_redeem_script) = create_funding_transaction(
        &pubkey_a,
        &pubkey_b,
        &inputs_a,
        &inputs_b,
        contrib_amount_a,
        contrib_amount_b,
        network,
        fee_rate_per_kw,
    );
    let funding_tx_amount = funding_transaction.output[0].value;
    let funding_tx_txid = funding_transaction.compute_txid();
    println!(
        "Funding transaction {}, id: {}",
        funding_tx_amount.to_sat(),
        funding_tx_txid
    );
    println!("    {}", encode_tx_to_hex(&funding_transaction));
    // println!("    {:?}", funding_transaction);
    // Process inputs of the funding tx, for saving
    let mut funding_inputs = Vec::<(u8, TxIn, u64)>::new();
    for (txin, value) in inputs_a {
        funding_inputs.push((0, txin.clone(), *value));
    }
    for (txin, value) in inputs_b {
        funding_inputs.push((1, txin.clone(), *value));
    }

    // let payout_a_address = Address::from_str(payout_a_address_str)
    //     .expect("Invalid address")
    //     .assume_checked();
    // let payout_b_address = Address::from_str(payout_b_address_str)
    //     .expect("Invalid address")
    //     .assume_checked();
    println!("A payout address: {}", payout_a_address.to_string());
    println!("B payout address: {}", payout_b_address.to_string());

    let refund_tx = create_refund_transaction(
        &payout_a_address,
        &payout_b_address,
        &funding_tx_txid,
        0,
        funding_transaction.output[0].value.to_sat(),
        contrib_amount_a,
        contrib_amount_b,
        fee_rate_per_kw,
        // network,
    );
    println!("Refund tx: {}", refund_tx.compute_txid());
    println!("    {}", encode_tx_to_hex(&refund_tx));
    println!("    {:?}", refund_tx);

    // create CETs, with the input of funding TX, and desired outcomes
    println!("Creating CETs...");
    let funding_amount = funding_transaction.output[0].value.to_sat();
    let input_funding = TxIn {
        previous_output: OutPoint {
            txid: funding_tx_txid,
            vout: 0,
        },
        ..Default::default()
    };
    let inputs_funding = vec![input_funding];
    let price_count = PRICE_MAX - PRICE_MIN + 1;
    let mut cets: Vec<CetInfo> = Vec::with_capacity(price_count as usize);
    for i in 0..price_count {
        let v = PRICE_MIN + i;
        if v % 100 == 0 {
            print!(" {} ", v);
        }

        let fee = estimate_fee(fee_rate_per_kw, 300, false);
        let remain_amount = funding_amount - fee;
        let (payout_a, payout_b) = payouts_for_a_and_b(target_price, v * 10, remain_amount);
        let mut outputs = Vec::new();
        if payout_a > 0 {
            outputs.push(TxOut {
                script_pubkey: payout_a_address.script_pubkey(),
                value: Amount::from_sat(payout_a),
            });
        }
        if payout_b > 0 {
            outputs.push(TxOut {
                script_pubkey: payout_b_address.script_pubkey(),
                value: Amount::from_sat(payout_b),
            });
        }
        let cet = Transaction {
            input: inputs_funding.clone(),
            output: outputs,
            version: Version::TWO,
            lock_time: LockTime::ZERO,
        };
        // let cet_txid = cet.compute_txid();
        let cet_sighash = &SighashCache::new(&cet)
            .p2wsh_signature_hash(
                0,
                &funding_redeem_script,
                funding_tx_amount,
                EcdsaSighashType::All,
            )
            .unwrap();
        // println!("CET {} {}", v, encode_tx_to_hex(&cet),);
        cets.push(CetInfo {
            raw_val: v as u32,
            tx: cet,
            sighash: cet_sighash.as_byte_array().clone(),
            adaptor_sig_a: None,
            adaptor_sig_b: None,
        });
    }
    println!("");
    println!("Created CETs, {}", cets.len());

    Ok(DlcTxs {
        funding_tx: funding_transaction,
        funding_inputs,
        funding_redeem_script,
        refund_tx,
        cets,
    })
}

fn verify_signature(msg: &[u8], sig: &[u8], pubkey: &PublicKey) -> Result<bool, String> {
    let m = Message::from_digest_slice(&msg).unwrap();
    let s = Signature::from_der(&sig).unwrap();
    let ctx = Secp256k1::new();
    match ctx.verify_ecdsa(&m, &s, &pubkey.inner) {
        Ok(_) => Ok(true),
        Err(e) => {
            let err = format!(
                "Signature verification failed! err {}  msg {}  sig {}  pk {}",
                e,
                &msg.as_hex(),
                &sig.as_hex(),
                &pubkey.to_string(),
            );
            println!("{}", err);
            Err(err)
        }
    }
}

/// This simulates the flow done by the two clients (i.e in the app)
fn sign_transactions_client(
    cli_no: u8,
    seckey: &SecretKey,
    pubkey: &PublicKey,
    txs: &mut DlcTxs,
    // oracle_api: &str,
    oracle_pubkey: &PublicKey,
    // duration_days: u32,
    event_info: &EventInfo,
) -> Result<(), Error> {
    println!("Client {}", cli_no);

    // Sign refund TX. That has one input -- the funding tx -- that has to be signed by both
    println!("Sign refund tx ({})", cli_no);
    assert_eq!(txs.refund_tx.input.len(), 1);
    let sighash = &SighashCache::new(&txs.refund_tx)
        .p2wsh_signature_hash(
            0,
            &txs.funding_redeem_script,
            txs.funding_tx.output[0].value,
            EcdsaSighashType::All,
        )
        .unwrap();

    println!("Sighash: {}", sighash.as_byte_array().to_lower_hex_string());
    let secp_ctx = Secp256k1::new();
    let m = Message::from_digest_slice(sighash.as_byte_array()).unwrap();
    let mut sig = secp_ctx.sign_ecdsa(&m, &seckey).serialize_der().to_vec();
    sig.push(EcdsaSighashType::All as u8);
    println!("sig: {}", sig.to_lower_hex_string());

    // verify sig
    assert!(verify_signature(sighash.as_byte_array(), &sig[0..sig.len() - 1], &pubkey).unwrap());

    // update signature as a witness
    // if we are cli 0, fill with 4 witness elements, with the other sig empty
    // println!(
    //     "redeem script {}",
    //     txs.funding_redeem_script.as_bytes().to_lower_hex_string()
    // );
    if cli_no == 0 {
        txs.refund_tx.input[0].witness = Witness::from_slice(&[
            &[][..],
            &sig,
            &[][..], // placeholder for other's sig
            &txs.funding_redeem_script.to_bytes(),
        ]);
    } else {
        // second client, only update our sig (elem idx=2)
        let mut witness_arr = txs.refund_tx.input[0].witness.to_vec().clone();
        witness_arr[2] = sig.to_vec();
        // println!(
        //     "witness_arr {}  lens {} {} {} {}",
        //     witness_arr.len(),
        //     witness_arr[0].len(),
        //     witness_arr[1].len(),
        //     witness_arr[2].len(),
        //     witness_arr[3].len()
        // );
        // println!(
        //     "witness_arr {}  lens \n  {}\n  {}\n  {}\n  {}",
        //     witness_arr.len(),
        //     witness_arr[0].to_lower_hex_string(),
        //     witness_arr[1].to_lower_hex_string(),
        //     witness_arr[2].to_lower_hex_string(),
        //     witness_arr[3].to_lower_hex_string(),
        // );
        // set it
        txs.refund_tx.input[0].witness = Witness::from_slice(&witness_arr);
    }
    println!("Signed refund tx");

    // Sign funding TX
    println!("Sign funding tx ({})", cli_no);
    assert_eq!(txs.funding_inputs.len(), txs.funding_tx.input.len());
    for i in 0..txs.funding_tx.input.len() {
        let (i_cli, _txin, value) = &txs.funding_inputs[i];
        if *i_cli == cli_no {
            println!("Input, val {} ...", value);
            let sighash = &SighashCache::new(&txs.funding_tx)
                .p2wpkh_signature_hash(
                    cli_no as usize,
                    ScriptBuf::new_p2wpkh(&pubkey.wpubkey_hash().unwrap()).as_script(),
                    Amount::from_sat(*value),
                    EcdsaSighashType::All,
                )
                .unwrap();
            println!("Sighash: {}", sighash.as_byte_array().to_lower_hex_string());
            let m = Message::from_digest_slice(sighash.as_byte_array()).unwrap();
            let mut sig = secp_ctx.sign_ecdsa(&m, &seckey).serialize_der().to_vec();
            sig.push(EcdsaSighashType::All as u8);
            println!("sig: {}", sig.to_lower_hex_string());

            // verify sig
            assert!(
                verify_signature(sighash.as_byte_array(), &sig[0..sig.len() - 1], &pubkey).unwrap()
            );

            // update signature as a witness
            txs.funding_tx.input[i].witness = Witness::from_slice(&[
                // &[][..],
                &sig,
                &pubkey.to_bytes(),
            ]);
        }
    }
    println!("Signed funding tx");

    let digits = event_info.range_digits;
    println!("Digits: {}", digits);
    let string_template = &event_info.string_template;
    println!("String template: '{}'", string_template);

    // Create adaptor signature points for each digit and outcome (count: digits x 10)
    println!("Creating adaptor signature points for each digit...");
    let mut sig_points: Vec<Vec<secp256k1_zkp::PublicKey>> = Vec::new();
    for d in 0..digits {
        let nonce_str = &event_info.nonces[d as usize];
        let nonce = pubkey_from_hex(nonce_str).unwrap();
        let mut sig_points_inner: Vec<secp256k1_zkp::PublicKey> = Vec::new();
        for v in 0..10 {
            let sig_point =
                create_digit_adaptor_sig_point(&oracle_pubkey, d, v, &string_template, &nonce)?;
            // println!("sig point {} {} {}", d, v, sig_point.to_string());
            sig_points_inner.push(sig_point);
        }
        sig_points.push(sig_points_inner);
    }
    println!("");

    // Loop through CETs
    println!(
        "Creating adaptor signatures for each CET... ({})",
        txs.cets.len()
    );
    let mut cnt = 0;
    for cet in &mut txs.cets {
        if cnt % 100 == 0 {
            print!(". ");
        }
        cnt += 1;
        let digits_vec = &value_to_digits(cet.raw_val);
        let mut keys = Vec::with_capacity(7);
        for i in 0..digits {
            keys.push(&sig_points[i as usize][digits_vec[i as usize] as usize]);
        }
        let aggr_sig_point = combine_pubkeys(keys.as_slice())?;
        // println!("aggr_sig_point {}", aggr_sig_point.to_string());

        let tx_sighash = &cet.sighash;

        // Creates adaptor signature
        #[cfg(feature = "std")]
        let adaptor_signature = EcdsaAdaptorSignature::encrypt(
            &secp_ctx,
            &Message::from_digest(*tx_sighash),
            &seckey,
            &aggr_sig_point,
        );
        if cli_no == 0 {
            cet.adaptor_sig_a = Some(adaptor_signature);
        } else {
            cet.adaptor_sig_b = Some(adaptor_signature);
        }
    }
    println!("");
    println!("done.");

    Ok(())
}

/// Obtain the simulated (dummy) output from the oracle
async fn obtain_oracle_outcome(oracle_api: &str, event_id: &str) -> EventWithOutcomeDto {
    let request_url = format!(
        "{}/v0/test_only/dummy_outcome_for_event/{}",
        oracle_api, event_id
    );
    // println!("request_url {}", request_url);

    let client = reqwest::Client::new();
    let response = client
        .get(request_url)
        // .header(USER_AGENT, "rust-web-api-client") // gh api requires a user-agent header
        .send()
        .await
        .expect("API error");

    let resp: EventWithOutcomeDto = response.json().await.expect("API error");
    resp
}

async fn sign_final_cet(
    cli_no: u8,
    seckey: &SecretKey,
    pubkey: &PublicKey,
    pubkey_other: &PublicKey,
    event_outcome: &EventWithOutcomeDto,
    txs: &mut DlcTxs,
) -> Result<(), Error> {
    // Find our cet
    println!(
        "Outcome value: {} {}",
        event_outcome.outcome_value, event_outcome.outcome_value as u64
    );
    // let raw_val = (event_outcome.outcome_value / 10f64).round() as u64;
    let raw_val = event_outcome.outcome_value as u64;
    let cet_idx = raw_val - PRICE_MIN;
    println!("Raw value: {}  cet idx {}", raw_val, cet_idx);

    // Find matching CET
    assert!(cet_idx < txs.cets.len() as u64);
    let cet_info = &mut txs.cets[cet_idx as usize];
    println!(
        "Found matching CET  {} {} {}",
        raw_val, cet_idx, cet_info.raw_val
    );
    assert_eq!(raw_val, cet_info.raw_val as u64);

    // Decompose oracle signatures
    println!("Decomposing adaptor signature...");
    assert_eq!(event_outcome.digits.len(), 7);
    let mut adaptor_secret_vec = Vec::new();
    for d in &event_outcome.digits {
        let sig_vec = <Vec<u8>>::from_hex(&d.signature).unwrap();
        let sig = SchnorrSignature::from_slice(&sig_vec).unwrap();
        let (_nonce, secret_value) = schnorrsig_decompose(&sig).unwrap();
        let adaptor_secret = SecretKey::from_slice(secret_value).unwrap();
        adaptor_secret_vec.push(adaptor_secret);
    }
    let adaptor_secret_aggregate = aggregate_secret_values(&adaptor_secret_vec);
    // Adaptor signature from the OTHER
    let adaptor_signature = if cli_no == 0 {
        &cet_info.adaptor_sig_b.unwrap()
    } else {
        &cet_info.adaptor_sig_a.unwrap()
    };
    let mut adapted_sig = adaptor_signature
        .decrypt(&adaptor_secret_aggregate)
        .unwrap()
        .serialize_der()
        .to_vec();
    // Adapted signature is variable, can't assert
    assert!(adapted_sig.len() >= 69 && adapted_sig.len() <= 71);
    adapted_sig.push(EcdsaSighashType::All as u8);
    println!(
        "Adapted signature: {}",
        adapted_sig.to_vec().to_lower_hex_string()
    );

    // verify signature
    {
        assert!(verify_signature(
            &cet_info.sighash,
            &adapted_sig[0..adapted_sig.len() - 1],
            &pubkey_other
        )
        .unwrap());
    }

    // Now sign the CET on my own part
    println!("Sign the CET...");
    println!("Sighash: {}", cet_info.sighash.to_lower_hex_string());

    let secp_ctx = Secp256k1::new();
    let m = Message::from_digest_slice(&cet_info.sighash).unwrap();
    let mut my_sig = secp_ctx.sign_ecdsa(&m, &seckey).serialize_der().to_vec();
    my_sig.push(EcdsaSighashType::All as u8);
    println!("My sig: {}", my_sig.to_lower_hex_string());

    // verify sig
    assert!(verify_signature(&cet_info.sighash, &my_sig[0..my_sig.len() - 1], &pubkey).unwrap());

    // update signature as a witness
    // println!(
    //     "redeem script {}",
    //     txs.funding_redeem_script.as_bytes().to_lower_hex_string()
    // );
    if cli_no == 0 {
        cet_info.tx.input[0].witness = Witness::from_slice(&[
            &[][..],
            &my_sig,
            &adapted_sig,
            &txs.funding_redeem_script.to_bytes(),
        ]);
    } else {
        cet_info.tx.input[0].witness = Witness::from_slice(&[
            &[][..],
            &adapted_sig,
            &my_sig,
            &txs.funding_redeem_script.to_bytes(),
        ]);
    }
    println!("Signed CET tx");
    println!("    id {}", cet_info.tx.compute_txid());
    println!("    hex {}", encode_tx_to_hex(&cet_info.tx));
    // println!("    {:?}", cet_info.tx);

    Ok(())
}
