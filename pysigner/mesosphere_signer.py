import argparse
import os
import requests
import sys
import time
import traceback

from typing import Dict, List, NoReturn

from box import Box
from dotenv import load_dotenv, find_dotenv
import telebot
from web3 import Web3
from web3.middleware import geth_poa_middleware
import yaml


def get_configs(args: List[str]) -> Box:
    """get all signer configurations from passed flags or yaml file"""

    # read in configurations from yaml file
    with open("../config.yml", "r") as ymlfile:
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
        type=str,
        help="Extra gwei added to gas price if gas price too low.",
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
        return f"""
            Asset: {self.name}
            \trequest_id: {self.request_id}
            \tprice: {self.price}
            \ttimestamp: {self.timestamp}
            """


def bot_alert(msg: str, prev_msg: str, asset: Asset) -> str:
    print(msg)
    message = f"asset/ID: {asset.name}/{asset.request_id}\n" + msg
    message = f"network: {network}\n" + message
    message = f"owner pub key: {acc.address[:6]}...\n" + message
    message = f'bot name: {os.getenv("BOT_NAME")}\n' + message
    if message != prev_msg and bot != None:
        bot.send_message(os.getenv("CHAT_ID"), message)
    return message


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
        print(msg)


def medianize_eth_dai(eth_apis: Dict, dai_apis: Dict) -> int:
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
            prices.append((eth_price / dai_price) * cfg.precision)

    prices.sort()
    return int(prices[int(len(prices) / 2)])


def medianize_prices(apis: Dict) -> int:
    prices = []
    for name in apis:
        price = get_price(apis[name])

        if price:
            prices.append(price * cfg.precision)

    prices.sort()
    return int(prices[int(len(prices) / 2)])


def update_assets() -> List[Asset]:
    eth_in_dai.timestamp = int(time.time())
    eth_dai_price = medianize_eth_dai(cfg.apis.eth, cfg.apis.dai)
    eth_in_dai.price = int(eth_dai_price)

    wbtc.timestamp = int(time.time())
    wbtc_price = medianize_prices(cfg.apis.wbtc)
    wbtc.price = wbtc_price

    return [eth_in_dai, wbtc]


def build_tx(
        an_asset: Asset, new_nonce: int, new_gas_price: str, extra_gas_price: float
) -> Dict:
    new_gas_price = str(float(new_gas_price) + extra_gas_price)

    transaction = mesosphere.functions.submitValue(
        an_asset.request_id, an_asset.price
    ).buildTransaction(
        {
            "nonce": new_nonce,
            "gas": 4000000,
            "gasPrice": w3.toWei(new_gas_price, "gwei"),
            "chainId": chain_id,
        }
    )

    print("gas price used:", new_gas_price)
    return transaction


def TellorSignerMain() -> NoReturn:
    prev_alert = ""
    current_asset = None
    while True:
        try:
            assets = update_assets()

            nonce = w3.eth.get_transaction_count(acc.address)

            for asset in assets:
                current_asset = asset
                print("nonce:", nonce)

                # if signer balance is less than half an ether, send alert
                if w3.eth.get_balance(acc.address) < 5e14:
                    msg = f"warning: signer balance now below .5 ETH\nCheck {explorer}/address/{acc.address}"
                    prev_alert = bot_alert(msg, prev_alert, asset)

                extra_gp = 0.0  # added to gas price to speed up tx if gas price too low

                while True:
                    try:
                        if extra_gp >= cfg.extra_gasprice_ceiling:
                            break

                        if (asset.timestamp - asset.time_last_pushed > 5) or (
                                abs(asset.price - asset.last_pushed_price) > 0.05
                        ):
                            tx = build_tx(
                                asset,
                                nonce,
                                new_gas_price=cfg.gasprice,
                                extra_gas_price=extra_gp,
                            )
                            print("tx built")

                            tx_signed = w3.eth.default_account.sign_transaction(tx)
                            print("tx signed")

                            tx_hash = w3.eth.send_raw_transaction(
                                tx_signed.rawTransaction
                            )
                            print("got tx hash")

                            _ = w3.eth.wait_for_transaction_receipt(
                                tx_hash, timeout=360
                            )
                            print("got tx receipt, tx sent")
                            nonce += 1
                    except Exception as e:
                        # traceback.print_exc()
                        tb = str(traceback.format_exc())
                        msg = str(e) + "\n"
                        err_msg = str(e.args)

                        # increase gas price if transaction timeout
                        if "timeout" in tb:
                            extra_gp += cfg.error_gasprice
                            msg += f"increased gas price by {cfg.error_gasprice} gwei"
                            continue

                        # reduce gas price if over threshold
                        elif "exceeds the configured cap" in err_msg:
                            msg += "reducing gas price"
                            extra_gp = 0.0

                        elif "replacement transaction underpriced" in err_msg:
                            extra_gp += cfg.error_gasprice
                            msg += f"increased gas price by {cfg.error_gasprice} gwei"

                        elif "nonce too low" in err_msg:
                            msg += "increasing nonce"
                            nonce += 1

                        elif "insufficient funds" in err_msg:
                            msg += f"Check {explorer}/address/{acc.address}\n"
                            prev_alert = bot_alert(msg, prev_alert, asset)

                        # nonce already used, leave while loop
                        elif "already known" in err_msg:
                            msg += f"skipping asset: {asset.name}"
                            break

                        # response from get_transaction_count or send_raw_transaction is None
                        elif "result" in err_msg:
                            msg += f"empty response from w3.eth.get_transaction_count(acc.address)"

                        # wait if error getting nonce with get_transaction_count
                        elif "RPC Error" in err_msg or "RPCError" in err_msg:
                            msg += f"RPC Error from w3.eth.get_transaction_count(acc.address)"
                            time.sleep(cfg.error_waittime)

                        # wait if too may requests sent
                        elif "https://rpc-mainnet.maticvigil.com/" in err_msg:
                            msg += f"too many requests in too little time. sleeping..."
                            time.sleep(cfg.error_waittime)

                        else:
                            msg = (
                                    "UNKNOWN ERROR\n" + msg + tb
                            )  # append traceback to alert if unknown error
                            prev_alert = bot_alert(msg, prev_alert, asset)

                        continue

                    break  # exit while loop if tx sent

                print(asset)

                asset.last_pushed_price = asset.price
                asset.time_last_pushed = asset.timestamp

                print("sleeping...")
                # wait because contract only writes new values every 60 seconds
                time.sleep(20)

                if w3.eth.get_balance(acc.address) < 0.005 * 1e18:
                    msg = f"urgent: signer ran out out of ETH\nCheck {explorer}/address/{acc.address}"
                    prev_alert = bot_alert(msg, prev_alert, asset)
                    time.sleep(60 * 15)

        except Exception as e:
            tb = str(traceback.format_exc())
            msg = str(e) + "\n" + tb
            prev_alert = bot_alert(msg, prev_alert, current_asset)
            continue


if __name__ == '__main__':

    btc = Asset("BTCUSD", 2)
    wbtc = Asset("WBTCUSD", 60)
    eth = Asset("ETHUSD", 1)
    dai = Asset("DAIUSD", 39)
    eth_in_dai = Asset("ETHDAI", 1)

    load_dotenv(find_dotenv())

    with open("../TellorMesosphere.json") as f:
        abi = f.read()

    cfg = get_configs(sys.argv[1:])

    network = cfg.network

    node = cfg.networks[network].node
    if network == "polygon":
        node += os.getenv("POKT_GATEWAY_ID")
    explorer = cfg.networks[network].explorer
    chain_id = cfg.networks[network].chain_id

    w3 = Web3(Web3.HTTPProvider(node))

    # choose network from CLI flag
    if network == "rinkeby" or network == "mumbai" or network == "rinkeby-arbitrum":
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    mesosphere = w3.eth.contract(Web3.toChecksumAddress(cfg.address), abi=abi)
    acc = w3.eth.default_account = w3.eth.account.from_key(os.getenv("PRIVATEKEY"))
    print("your address", acc.address)
    print("your balance", w3.eth.get_balance(acc.address))

    bot = None
    if os.getenv("TG_TOKEN") != None and os.getenv("CHAT_ID") != None:
        bot = telebot.TeleBot(os.getenv("TG_TOKEN"), parse_mode=None)

    TellorSignerMain()
