// Copyright (c) 2025-present Cadena Bitcoin
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

/// Playground for Discrete Log Contracts (DLC) and Adaptor Signatures, written in Rust, focusing on the cryptography.
/// Partly insipred by [rust-dlc](https://github.com/p2pderivatives/rust-dlc)
mod adaptor_flow;
mod crypto;
mod full_flow;

use crate::adaptor_flow::{main_usecase, usecase_with_digits};
use crate::full_flow::full_use_case_main;

#[tokio::main]
async fn main() {
    main_usecase();

    usecase_with_digits();

    full_use_case_main().await;
}
