# StarkwareSigner

## General

A python library + script for requesting, standardizing, and signing price feeds.

## Installation

### Python Dependencies

Required packages can be installed with `pipenv install`.
Refer (here)[https://pipenv.pypa.io/en/latest/install/#pragmatic-installation-of-pipenv] for `pipenv` installation instructions if you do not have `pipenv` preinstalled.

### Environment variables

StarkwareSigner takes advantage of the `python-dotenv` module, which reads environment variables from a `.env` file. This `.env` file is where you may store your ETH private key. StarkwareSigner will read from the `.env` file in order to create a Starkware Key from your ETH Key.

## Script Walkthrough

### Requesting

StarkwareSigner requests centralized price feeds for BTC/USD and ETH/USD from:
* Coinbase
* Coingecko
* Bittrex
* Gemini
* Kraken

### Standardizing

StarkwareSigner then medianizes last submitted prices from each source, formatting price and metadata as JSON to be signed.

### Signing

Data subissions are signed with Starkware signing technology.
