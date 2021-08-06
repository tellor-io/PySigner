import argparse
import json
import os
import requests
import time
import traceback

from dotenv import load_dotenv, find_dotenv
import telebot
from web3 import Web3
from web3.middleware import geth_poa_middleware

load_dotenv(find_dotenv())

with open('abi.json') as f:
    abi = f.read()

with open('config.json') as f:
    config = json.loads(f.read())[0]

with open('TellorMesosphere.json') as f:
    abi = f.read()


# Building CLI interface
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

contract_address = config['address']

bot = telebot.TeleBot(os.getenv("TG_TOKEN"), parse_mode=None)
private_key = os.getenv("PRIVATEKEY")
myName = "Tellor"
w3 = Web3(Web3.HTTPProvider(node))

# Choose network from CLI flag
if network == "rinkeby" or network == "mumbai" or network == "rinkeby-arbitrum":
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
mesosphere = w3.eth.contract(
    Web3.toChecksumAddress(contract_address),
    abi=abi
)

acc = w3.eth.default_account = w3.eth.account.from_key(private_key)
precision = 1e6

print('your address', acc.address)
print('your balance', w3.eth.get_balance(acc.address))
# BTC and ETH api endpoints from centralized exchanges
# Each endpoint is encased in a list with the keywords that parse the JSON
# to the last price

btcAPIs = [
    ["https://api.pro.coinbase.com/products/BTC-USD/ticker", "price"],
    ["https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", "bitcoin", "usd"],
    ["https://api.bittrex.com/api/v1.1/public/getticker?market=USD-BTC", 'result', 'Last'],
    ["https://api.gemini.com/v1/pubticker/btcusd", 'last'],
    ["https://api.kraken.com/0/public/Ticker?pair=TBTCUSD", 'result', "TBTCUSD", 'c', 0]

]

ethAPIs = [
    ["https://api.pro.coinbase.com/products/ETH-USD/ticker", "price"],
    ["https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd", "ethereum", "usd"],
    ["https://api.bittrex.com/api/v1.1/public/getticker?market=USD-ETH", 'result', 'Last'],
    ["https://api.gemini.com/v1/pubticker/ethusd", 'last'],
    ["https://api.kraken.com/0/public/Ticker?pair=ETHUSDC", 'result', "ETHUSDC", 'c', 0]
]

daiAPIs = [
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

# final data submission format

submitData = {
    # "starkKey":0,
    "timestamp": 0,
    "price": 0,
    "assetName": 0,  # btc or eth
    "oracleName": 0,
    # "signatureR":0,
    # "signatureS":0
}


def fetchAPI(public_api):
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
    except BaseException:
        response = 0
        print('API ERROR', public_api[0])


def getAPIValues():
    eth_in_dai["timestamp"] = int(time.time())
    price = medianize(ethAPIs, daiAPIs)
    eth_in_dai["price"] = int(price)

    return [eth_in_dai]


def medianize(_ethAPIs, _daiAPIs):
    '''
    Medianizes price of an asset from a selection of centralized price APIs
    '''
    finalRes = []
    didGet = False
    n = 0
    for i, j in zip(_ethAPIs, _daiAPIs):
        _resETH = fetchAPI(i)
        _resDAI = fetchAPI(j)
        if not _resETH:
            continue
        if not _resDAI:
            continue
        if _resETH is None:
            continue
        if _resDAI is None:
            continue
        if _resETH > 0 and _resDAI > 0:
            didGet = True
            # finalRes.append(int(int(_resETH*(precision)) / int(_resDAI*(precision)))*precision)
            finalRes.append(int((_resETH / _resDAI) * precision))

    # sort final results
    finalRes.sort()
    return finalRes[int(len(finalRes) / 2)]


def TellorSignerMain():
    while True:
        alert_sent = False
        try:
            assets = getAPIValues()
        except BaseException:
            if not alert_sent:
                tb = traceback.format_exc()
                bot.send_message(os.getenv("CHAT_ID"), str(tb))
                alert_sent = True
        for asset in assets:
            try:
                nonce = w3.eth.get_transaction_count(acc.address)
                print('nonce:', nonce)
                # if signer balance is less than half an ether, send alert
                if (w3.eth.get_balance(acc.address) < 5E14) and ~alert_sent:
                    bot.send_message(
                        os.getenv("CHAT_ID"),
                        f'''warning: signer balance now below .5 ETH
					\nCheck {explorer}/address/''' + acc.address)
                    alert_sent = True
                else:
                    alert_sent = False
                if (asset["timestamp"] -
                    asset["timeLastPushed"] > 5) or (abs(asset["price"] -
                                                         asset["lastPushedPrice"]) > .05):
                    tx = mesosphere.functions.submitValue(asset['requestId'], asset['price']).buildTransaction(
                        {
                            'nonce': nonce,
                            'gas': 4000000,
                            'gasPrice': w3.toWei('3', 'gwei'),
                            'chainId': chainId
                        }
                    )
                    tx_signed = w3.eth.default_account.sign_transaction(tx)
            except BaseException:
                if not alert_sent:
                    tb = traceback.format_exc()
                    breakpoint()
                    bot.send_message(os.getenv("CHAT_ID"), str(tb))
                    alert_sent = True
            try:
                tx_hash = w3.eth.send_raw_transaction(tx_signed.rawTransaction)
                tx_receipt = w3.eth.wait_for_transaction_receipt(
                    transaction_hash=tx_hash,
                    timeout=360)
                print('tx sent')
            except ValueError as e:
                traceback.print_exc()
                nonce += 1
                break
            try:
                print('asset:', asset['asset'])
                print('asset price:', asset['price'])

                asset["lastPushedPrice"] = asset["price"]
                asset["timeLastPushed"] = asset["timestamp"]
                nonce += 1
                print("waiting to submit....")
                time.sleep(20)
            except BaseException:
                nonce += 1
                if w3.eth.get_balance(acc.address) < 0.005 * 1E18:
                    bot.send_message(
                        os.getenv("CHAT_ID"),
                        f'''urgent: signer ran out out of ETH"
					\nCheck {explorer}/address/{acc.address}''')
                    time.sleep(60 * 15)


TellorSignerMain()
