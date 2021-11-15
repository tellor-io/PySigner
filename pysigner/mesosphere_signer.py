import argparse
import csv
import logging
import os
import random
import sys
import time
import traceback
from typing import Dict
from typing import List

import requests
import telebot
import yaml
from box import Box
from dotenv import find_dotenv
from dotenv import load_dotenv
from hexbytes import HexBytes
from web3 import Web3
from web3.middleware import geth_poa_middleware

# create logs folder/contents if it does not yet exist
if not os.path.exists("logs/"):
    os.makedirs("logs/")

# create logs folder/contents if it does not yet exist
if not os.path.exists("logs/"):
    os.makedirs("logs/")


# set up logging for transaction data
tx_data_log = logging.getLogger("transactions")
tx_data_log.setLevel(logging.INFO)

formatter = logging.Formatter("%(message)s")
csv_handler = logging.FileHandler("logs/tx_data.csv")
csv_handler.setFormatter(formatter)

tx_data_log.addHandler(csv_handler)

# set up logging for expected TellorSigner info & errors
signer_log = logging.getLogger("signer")
signer_log.setLevel(logging.INFO)

signer_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
log_handler = logging.FileHandler("logs/signer.log")
log_handler.setFormatter(signer_formatter)

signer_log.addHandler(log_handler)


def get_configs(args: List[str]) -> Box:
    """get all signer configurations from passed flags or yaml file"""

    # read in configurations from yaml file
    with open("config.yml") as ymlfile:
        config = yaml.safe_load(ymlfile)

    # parse command line flags & arguments
    parser = argparse.ArgumentParser(description="Submit values to Tellor Mesosphere")
    parser.add_argument(
        "-n",
        "--network",
        nargs=1,
        required=False,
        type=str,
        help="An EVM compatible network.",
    )
    parser.add_argument(
        "-gp",
        "--gasprice",
        nargs=1,
        required=False,
        type=str,
        help="The gas price used for transactions. If no gas price is set, it is retrieved from https://gasstation-mainnet.matic.network.",
    )
    parser.add_argument(
        "-egp",
        "--error-gasprice",
        nargs=1,
        required=False,
        type=float,
        help="Extra gwei added to gas price if gas price too low.",
    )
    parser.add_argument(
        "-pk",
        "--private-key",
        nargs=1,
        required=False,
        type=str,
        help="an ethereum private key",
    )

    # get dict of parsed args
    cli_cfg = vars(parser.parse_args(args))

    # overwrite any configs from yaml file also given by user via cli
    for flag, arg in cli_cfg.items():
        if arg != None:
            config[flag] = arg[0]

    # enable dot notation for accessing configs
    config = Box(config)

    return config


# Asset is a helper class used to distinguish btc prices and eth prices
# these are used for data wrangling, from centralized API endpoints to
# medianization


class Asset:
    def __init__(self, name, request_id):
        self.name = name
        self.request_id = request_id
        self.price = 0
        self.str_price = ""
        self.timestamp = 0
        self.last_pushed_price = 0
        self.time_last_pushed = 0

    def __str__(self):
        return f"""Asset: {self.name} request_id: {self.request_id} price: {self.price} timestamp: {self.timestamp}"""

    def __repr__(self):
        return f"""Asset: {self.name} request_id: {self.request_id} price: {self.price} timestamp: {self.timestamp}"""

    def __eq__(self, other):
        if self.name == other.name and self.request_id == other.request_id:
            return True
        return False


def get_price(api_info: Dict) -> float:
    """
    Fetches price data from centralized public web API endpoints
    Returns: (str) ticker price from public exchange web APIs
    Input: (list of str) public api endpoint with any necessary json parsing keywords
    """
    try:
        # Request JSON from public api endpoint
        rsp = requests.get(api_info["url"]).json()

        # Parse through json with pre-written keywords
        for keyword in api_info["keywords"]:
            rsp = rsp[keyword]

        # return price (last remaining element of the json)
        price = float(rsp)
        return price

    except Exception as e:
        api_err_msg = f'API ERROR {api_info["url"]}\n'
        tb = str(traceback.format_exc())
        msg = api_err_msg + str(e) + "\n" + tb
        signer_log.error(msg)


def medianize_eth_dai(eth_apis: Dict, dai_apis: Dict, precision: int) -> int:
    """
    Medianizes price of an asset from a selection of centralized price APIs
    """
    prices = []
    for name1, name2 in zip(sorted(list(eth_apis)), sorted(list(dai_apis))):
        eth_price = get_price(eth_apis[name1])
        dai_price = get_price(dai_apis[name2])

        if eth_price is None or dai_price is None:
            continue

        if eth_price > 0 and dai_price > 0:
            prices.append((eth_price / dai_price) * precision)

    return medianize(prices)


def medianize_prices(apis: Dict, precision: int) -> int:
    prices = []
    for name in apis:
        price = get_price(apis[name])

        if price:
            prices.append(price * precision)

    return medianize(prices)


def medianize(prices: List[float]) -> int:
    prices.sort()
    return int(prices[int(len(prices) / 2)])


class TellorSigner:
    def __init__(self, cfg, private_key):
        signer_log.info("starting TellorSigner")
        self.cfg = cfg

        load_dotenv(find_dotenv())
        self.secret_test = os.getenv("TEST_VAR")

        with open("TellorMesosphere.json") as f:
            abi = f.read()

        network = self.cfg.network
        feeds = self.cfg.feeds

        # Only submit assets tipped on this network
        self.assets = [
            Asset(a, feeds[a].requestId)
            for a in feeds.keys()
            if feeds[a].networks != "none" and network in feeds[a].networks
        ]

        node = self.cfg.networks[network].node
        if network == "polygon":
            node += os.getenv("POKT_POLYGON")
        if network == "rinkeby":
            node += os.getenv("POKT_RINKEBY")
        self.explorer = self.cfg.networks[network].explorer
        self.chain_id = self.cfg.networks[network].chain_id

        self.w3 = Web3(Web3.HTTPProvider(node))

        # choose network from CLI flag
        if network == "rinkeby" or network == "mumbai" or network == "rinkeby-arbitrum":
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.mesosphere = self.w3.eth.contract(
            Web3.toChecksumAddress(self.cfg.address[network]), abi=abi
        )
        self.acc = self.w3.eth.default_account = self.w3.eth.account.from_key(
            private_key if private_key else os.getenv("PRIVATE_KEYS")
        )

        self.bot = None
        if os.getenv("TG_TOKEN") != None and os.getenv("CHAT_ID") != None:
            self.bot = telebot.TeleBot(os.getenv("TG_TOKEN"), parse_mode=None)

    def bot_alert(self, msg: str, prev_msg: str, asset: Asset) -> str:
        message = f"""
        bot name: {os.getenv("BOT_NAME")}
        owner pub key: {self.acc.address[:6]}...
        network: {self.cfg.network}
        asset/ID: {asset.name}/{asset.request_id}
        {msg}
        """
        if message != prev_msg and self.bot != None:
            self.bot.send_message(os.getenv("CHAT_ID"), message)
            signer_log.info(f"telegram alert sent: \n{msg}")
        return message

    def update_assets(self):
        updated_assets = []

        for asset in self.assets:
            asset.timestamp = int(time.time())

            if asset.name == "ETHDAI":
                price = medianize_eth_dai(
                    self.cfg.apis.ETHUSD, self.cfg.apis.DAIUSD, self.cfg.precision
                )
            elif asset.name == "random_int":
                price = random.SystemRandom().randint(a=0, b=1e6)
            else:
                price = medianize_prices(self.cfg.apis[asset.name], self.cfg.precision)
            asset.price = price

            updated_assets.append(asset)

        self.assets = updated_assets

    def build_tx(
        self,
        an_asset: Asset,
        new_nonce: int,
        new_gas_price: str,
        extra_gas_price: float,
    ) -> Dict:
        new_gas_price = str(float(new_gas_price) + extra_gas_price)

        transaction = self.mesosphere.functions.submitValue(
            an_asset.request_id, an_asset.price
        ).buildTransaction(
            {
                "nonce": new_nonce,
                "gas": 4000000,
                "gasPrice": self.w3.toWei(new_gas_price, "gwei"),
                "chainId": self.chain_id,
            }
        )

        return transaction

    def log_tx(self, asset: Asset, tx_hash: HexBytes):
        rows = f"{asset.timestamp},{asset.name},{asset.price},{asset.request_id},{tx_hash.hex()},{self.cfg.network}"
        tx_data_log.info(rows)

    def run(self):
        signer_log.info(f"your address: {self.acc.address}")
        starting_balance = self.w3.eth.get_balance(self.acc.address)
        signer_log.info(f"your balance: {starting_balance}")

        prev_alert = ""
        current_asset = None
        while True:
            try:
                self.update_assets()

                nonce = self.w3.eth.get_transaction_count(self.acc.address)

                for i, asset in enumerate(self.assets):
                    current_asset = asset
                    print("nonce:", nonce)

                    # if signer balance is less than half an ether, send alert
                    if self.w3.eth.get_balance(self.acc.address) < 5e14:
                        msg = f"warning: signer balance now below .5 ETH\nCheck {self.explorer}/address/{self.acc.address}"
                        signer_log.warning(msg)
                        prev_alert = self.bot_alert(msg, prev_alert, asset)

                    extra_gp = (
                        0.0  # added to gas price to speed up tx if gas price too low
                    )

                    while True:
                        try:
                            if extra_gp >= self.cfg.extra_gasprice_ceiling:
                                signer_log.info(
                                    "exceeded gas price ceiling, resetting extra gas price"
                                )
                                extra_gp = 0.0
                                break

                            if (asset.timestamp - asset.time_last_pushed > 5) or (
                                abs(asset.price - asset.last_pushed_price) > 0.05
                            ):
                                tx = self.build_tx(
                                    asset,
                                    nonce,
                                    new_gas_price=self.cfg.gasprice,
                                    extra_gas_price=extra_gp,
                                )

                                tx_signed = (
                                    self.w3.eth.default_account.sign_transaction(tx)
                                )

                                tx_hash = self.w3.eth.send_raw_transaction(
                                    tx_signed.rawTransaction
                                )

                                print("waiting for tx receipt")
                                _ = self.w3.eth.wait_for_transaction_receipt(
                                    tx_hash, timeout=self.cfg.receipt_timeout
                                )
                                print("received, tx sent")

                                self.log_tx(asset, tx_hash)
                                nonce += 1
                        except Exception as e:
                            tb = str(traceback.format_exc())
                            msg = str(e) + "\n"
                            err_msg = str(e.args)
                            err_log = msg + err_msg + tb

                            # increase gas price if transaction timeout
                            if "timeout" in tb:
                                extra_gp += self.cfg.error_gasprice
                                msg += f"increased gas price by {self.cfg.error_gasprice} gwei"
                                signer_log.info(msg)
                                continue

                            # reduce gas price if over threshold
                            elif "exceeds the configured cap" in err_msg:
                                msg += "reducing gas price"
                                extra_gp = 0.0
                                signer_log.info(msg)

                            elif "replacement transaction underpriced" in err_msg:
                                extra_gp += self.cfg.error_gasprice
                                msg += f"increased gas price by {self.cfg.error_gasprice} gwei"
                                signer_log.info(msg)

                            elif "nonce too low" in err_msg:
                                msg += "increasing nonce"
                                nonce += 1
                                signer_log.info(msg)

                            elif "insufficient funds" in err_msg:
                                msg += f"Check {self.explorer}/address/{self.acc.address}\n"
                                signer_log.warning(msg)
                                prev_alert = self.bot_alert(msg, prev_alert, asset)

                            # nonce already used, leave while loop
                            elif "already known" in err_msg:
                                msg += f"skipping asset: {asset.name}"
                                signer_log.info(msg)
                                break

                            # response from get_transaction_count or send_raw_transaction is None
                            elif "result" in err_log:
                                msg += f"empty response from w3.eth.get_transaction_count(acc.address)"
                                signer_log.info(msg)

                            # wait if error getting nonce with get_transaction_count
                            elif "RPC Error" in err_log or "RPCError" in err_log:
                                msg += f"RPC Error from w3.eth.get_transaction_count(acc.address)"
                                signer_log.info(msg)
                                time.sleep(self.cfg.error_waittime)

                            # wait if too many requests sent
                            elif "https://rpc-mainnet.maticvigil.com/" in err_msg:
                                msg += (
                                    f"too many requests in too little time. sleeping..."
                                )
                                signer_log.info(msg)
                                time.sleep(self.cfg.error_waittime)

                            else:
                                msg = (
                                    "UNKNOWN ERROR\n" + msg + tb
                                )  # append traceback to alert if unknown error
                                signer_log.error(msg)
                                prev_alert = self.bot_alert(msg, prev_alert, asset)

                            continue

                        break  # exit while loop if tx sent

                    print(asset)

                    self.assets[i].last_pushed_price = asset.price
                    self.assets[i].time_last_pushed = asset.timestamp

                    time.sleep(3600)
                    print("sleeping...")
                    # wait because contract only writes new values every 60 seconds

                    curr_balance = self.w3.eth.get_balance(self.acc.address)
                    if curr_balance < 0.005 * 1e18:
                        msg = f"urgent: refill balance now (currently: {curr_balance}) \nCheck {self.explorer}/address/{self.acc.address}"
                        signer_log.warning(msg)
                        prev_alert = self.bot_alert(msg, prev_alert, asset)
                        time.sleep(60 * 15)

            except Exception as e:
                tb = str(traceback.format_exc())
                msg = str(e) + "\n" + tb
                signer_log.error(msg)
                prev_alert = self.bot_alert(msg, prev_alert, current_asset)


if __name__ == "__main__":
    cfg = get_configs(sys.argv[1:])
    signer = TellorSigner(cfg)
    signer.run()
