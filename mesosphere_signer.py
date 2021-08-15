import argparse
import json
import os
import requests
import time
import traceback

from typing import Dict, List, NoReturn, Union

from dotenv import load_dotenv, find_dotenv
import telebot
from web3 import Web3
from web3.middleware import geth_poa_middleware


load_dotenv(find_dotenv())

with open('config.json') as f:
    config = json.loads(f.read())[0]

with open('TellorMesosphere.json') as f:
    abi = f.read()

# build CLI interface
parser = argparse.ArgumentParser(
    description='Submit values to Tellor Mesosphere')
parser.add_argument(
    '-n',
    '--network',
    nargs=1,
    required=True,
    type=str,
    help="an EVM compatible network")
args = parser.parse_args()
network = args.network[0]

node = config['networks'][network]['node']
if network == 'rinkeby':
    node += os.getenv('INFURA_KEY')
explorer = config['networks'][network]['explorer']
chainId = config['networks'][network]['chainId']

w3 = Web3(Web3.HTTPProvider(node))

# choose network from CLI flag
if network == "rinkeby" or network == "mumbai" or network == "rinkeby-arbitrum":
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
mesosphere = w3.eth.contract(
    Web3.toChecksumAddress(config['address']),
    abi=abi
)
acc = w3.eth.default_account = w3.eth.account.from_key(os.getenv("PRIVATEKEY"))
print('your address', acc.address)
print('your balance', w3.eth.get_balance(acc.address))

bot = telebot.TeleBot(os.getenv("TG_TOKEN"), parse_mode=None)

PRECISION = 1e6

# api endpoints from centralized exchanges
# Each endpoint is encased in a list with the keywords that parse the JSON
# to the last price

BTC_APIS = [
    ["https://api.pro.coinbase.com/products/BTC-USD/ticker", "price"],
    ["https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", "bitcoin", "usd"],
    ["https://api.bittrex.com/api/v1.1/public/getticker?market=USD-BTC", 'result', 'Last'],
    ["https://api.gemini.com/v1/pubticker/btcusd", 'last'],
    ["https://api.kraken.com/0/public/Ticker?pair=TBTCUSD", 'result', "TBTCUSD", 'c', 0]

]

WBTC_APIS = [
    ["https://api.pro.coinbase.com/products/WBTC-USD/ticker", "price"],
    ["https://api.coingecko.com/api/v3/simple/price?ids=wrapped-bitcoin&vs_currencies=usd", "usd"],
    ["https://api.bittrex.com/api/v1.1/public/getticker?market=USDT-WBTC", 'result', 'Last'],
    ["https://api.kraken.com/0/public/Ticker?pair=WBTCUSD", 'result', "WBTCUSD", 'c', 0]

]

ETH_APIS = [
    ["https://api.pro.coinbase.com/products/ETH-USD/ticker", "price"],
    ["https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd", "ethereum", "usd"],
    ["https://api.bittrex.com/api/v1.1/public/getticker?market=USD-ETH", 'result', 'Last'],
    ["https://api.gemini.com/v1/pubticker/ethusd", 'last'],
    ["https://api.kraken.com/0/public/Ticker?pair=ETHUSDC", 'result', "ETHUSDC", 'c', 0]
]

DAI_APIS = [
    ["https://api.pro.coinbase.com/products/DAI-USD/ticker", "price"],
    ["https://api.coingecko.com/api/v3/simple/price?ids=dai&vs_currencies=usd", "dai", "usd"],
    ["https://api.bittrex.com/api/v1.1/public/getticker?market=USD-DAI", 'result', 'Last'],
    ["https://api.gemini.com/v1/pubticker/daiusd", 'last'],
    ["https://api.kraken.com/0/public/Ticker?pair=DAIUSD", 'result', "DAIUSD", 'c', 0]

]

# btc, eth are helper dictionaries used to distinguish btc prices and eth prices
# these are used for data wrangling, from centralized API endpoints to
# medianization

btc = {
    "requestId": 2,
    "price": 0,
    "strPrice": "",
    "asset": "BTCUSD",
    "timestamp": 0,
    "lastPushedPrice": 0,
    "timeLastPushed": 0
}

wbtc = {
    "requestId": 60,
    "price": 0,
    "asset": "WBTCUSD",
    "strPrice": "",
    "timestamp": 0,
    "lastPushedPrice": 0,
    "timeLastPushed": 0
}

eth = {
    "requestId": 1,
    "price": 0,
    "asset": "ETHUSD",
    "strPrice": "",
    "timestamp": 0,
    "lastPushedPrice": 0,
    "timeLastPushed": 0
}

dai = {
    "requestId": 39,
    "price": 0,
    "asset": "DAIUSD",
    "strPrice": "",
    "timestamp": 0,
    "lastPushedPrice": 0,
    "timeLastPushed": 0
}

eth_in_dai = {
    "requestId": 1,
    "price": 0,
    "asset": "ETHDAI",
    "strPrice": "",
    "timestamp": 0,
    "lastPushedPrice": 0,
    "timeLastPushed": 0
}


def bot_alert(msg: str, prev_msg: str) -> str:
    print(msg)
    message = f'from: {os.getenv("BOT_NAME")}\n' + msg
    if message != prev_msg:
        bot.send_message(os.getenv("CHAT_ID"), message)
    return message


def get_price(public_api: List[Union[str, int]]) -> float:
    '''
    Fetches price data from centralized public web API endpoints
    Returns: (str) ticker price from public exchange web APIs
    Input: (list of str) public api endpoint with any necessary json parsing keywords
    '''
    try:
        # Parse list input
        endpoint = public_api[0]
        parsers = public_api[1:]

        # Request JSON from public api endpoint
        r = requests.get(endpoint)
        json_ = r.json()

        # Parse through json with pre-written keywords
        for keyword in parsers:
            json_ = json_[keyword]

        # return price (last remaining element of the json)
        price = json_
        return float(price)

    except Exception as e:
        api_err_msg = f'API ERROR {public_api[0]}\n'
        tb = str(traceback.format_exc())
        msg = api_err_msg + str(e) + '\n' + tb
        print(msg)


def update_assets() -> List[Dict]:
    eth_in_dai["timestamp"] = int(time.time())
    price = medianize(ETH_APIS, DAI_APIS)
    eth_in_dai["price"] = int(price)

    wbtc["timestamp"] = int(time.time())

    return [eth_in_dai, wbtc]


def medianize(eth_apis: List[Union[str, int]], dai_apis: List[Union[str, int]]) -> List[int]:
    '''
    Medianizes price of an asset from a selection of centralized price APIs
    '''
    prices = []
    for i, j in zip(eth_apis, dai_apis):
        eth_price = get_price(i)
        dai_price = get_price(j)

        if eth_price == None or dai_price == None:
            continue

        if eth_price > 0 and dai_price > 0:
            prices.append(int((eth_price / dai_price) * PRECISION))

    prices.sort()
    return prices[int(len(prices) / 2)]


def build_tx(an_asset: Dict, new_nonce: int, new_gas_price: str, extra_gas_price: float) -> Dict:
    if new_gas_price == None:
        try:
            r = requests.get('https://gasstation-mainnet.matic.network').json()
            new_gas_price = str(r['standard'])
            print('retrieved gas price:', new_gas_price)
        except Exception as e:
            fallback_msg = 'unable to retrieve gas price, using fallback: 10\n'
            tb = str(traceback.format_exc())
            msg = fallback_msg + str(e) + '\n' + tb
            print(msg)
            new_gas_price = '10'

    new_gas_price = str(float(new_gas_price) + extra_gas_price)

    transaction = mesosphere.functions.submitValue(
        an_asset['requestId'],
        an_asset['price']).buildTransaction(
        {
            'nonce': new_nonce,
            'gas': 4000000,
            'gasPrice': w3.toWei(
                new_gas_price,
                'gwei'),
            'chainId': chainId})
    
    print('gas price used:', new_gas_price)
    return transaction


def TellorSignerMain() -> NoReturn:
    prev_alert = ''
    while True:
        try:
            assets = update_assets()

            nonce = w3.eth.get_transaction_count(acc.address)

            for asset in assets:
                print('nonce:', nonce)

                # if signer balance is less than half an ether, send alert
                if (w3.eth.get_balance(acc.address) < 5E14):
                    msg = f'warning: signer balance now below .5 ETH\nCheck {explorer}/address/{acc.address}'
                    prev_alert = bot_alert(msg, prev_alert)

                extra_gp = 0.  # added to gas price to speed up tx if gas price too low

                while True:
                    try:
                        if (asset["timestamp"] - asset["timeLastPushed"] > 5) or \
                                (abs(asset["price"] - asset["lastPushedPrice"]) > .05):
                            tx = build_tx(
                                asset,
                                nonce,
                                new_gas_price='3',
                                extra_gas_price=extra_gp)
                            print('tx built')

                            tx_signed = w3.eth.default_account.sign_transaction(
                                tx)
                            print('tx signed')

                            tx_hash = w3.eth.send_raw_transaction(
                                tx_signed.rawTransaction)
                            print('got tx hash')

                            _ = w3.eth.wait_for_transaction_receipt(
                                tx_hash, timeout=360)
                            print('got tx receipt, tx sent')
                            nonce += 1
                    except Exception as e:
                        # traceback.print_exc()
                        tb = str(traceback.format_exc())
                        msg = str(e) + '\n'
                        err_msg = str(e.args)

                        # increase gas price if transaction timeout
                        if 'timeout' in tb:
                            extra_gp += 50.
                            msg += 'increased gas price by 50'
                            prev_alert = bot_alert(msg, prev_alert)
                            continue

                        # reduce gas price if over threshold
                        elif 'exceeds the configured cap' in err_msg:
                            msg += 'reducing gas price'
                            extra_gp = 0.
                        
                        elif 'replacement transaction underpriced' in err_msg:
                            msg += 'increased gas price by 50'
                            extra_gp += 50.

                        elif 'nonce too low' in err_msg:
                            msg += 'increasing nonce'
                            nonce += 1

                        # nonce already used, leave while loop
                        elif 'already known' in err_msg:
                            msg += f'skipping asset: {asset["asset"]}'
                            prev_alert = bot_alert(msg, prev_alert)
                            break

                        else:
                            msg += tb # append traceback to alert if unknown error

                        prev_alert = bot_alert(msg, prev_alert)

                        continue

                    break  # exit while loop if tx sent

                print('asset:', asset['asset'])
                print('asset price:', asset['price'])

                asset["lastPushedPrice"] = asset["price"]
                asset["timeLastPushed"] = asset["timestamp"]

                print("sleeping...")
                # wait because contract only writes new values every 60 seconds
                time.sleep(20)

                if w3.eth.get_balance(acc.address) < 0.005 * 1E18:
                    msg = f'urgent: signer ran out out of ETH\nCheck {explorer}/address/{acc.address}'
                    prev_alert = bot_alert(msg, prev_alert)
                    time.sleep(60 * 15)

        except Exception as e:
            tb = str(traceback.format_exc())
            msg = str(e) + '\n' + tb
            prev_alert = bot_alert(msg, prev_alert)
            continue


TellorSignerMain()
