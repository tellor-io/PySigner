import os
import time

import requests
from dotenv import find_dotenv
from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import geth_poa_middleware

load_dotenv(find_dotenv())

private_key = os.getenv("PRIVATEKEY")
node = os.getenv("NODE")
myName = "Tellor"
w3 = Web3(Web3.HTTPProvider(node))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

with open("abi.json") as f:
    abi = f.read()

tellor_playground = w3.eth.contract(
    Web3.toChecksumAddress("0x20374E579832859f180536A69093A126Db1c8aE9"), abi=abi
)

acc = w3.eth.default_account = w3.eth.account.from_key(private_key)
print("your address", acc.address)
print("your balance", w3.eth.get_balance(acc.address))
# BTC and ETH api endpoints from centralized exchanges
# Each endpoint is encased in a list with the keywords that parse the JSON to the last price

btcAPIs = [
    ["https://api.pro.coinbase.com/products/BTC-USD/ticker", "price"],
    [
        "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
        "bitcoin",
        "usd",
    ],
    [
        "https://api.bittrex.com/api/v1.1/public/getticker?market=USD-BTC",
        "result",
        "Last",
    ],
    ["https://api.gemini.com/v1/pubticker/btcusd", "last"],
    [
        "https://api.kraken.com/0/public/Ticker?pair=TBTCUSD",
        "result",
        "TBTCUSD",
        "c",
        0,
    ],
]

ethAPIs = [
    ["https://api.pro.coinbase.com/products/ETH-USD/ticker", "price"],
    [
        "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd",
        "ethereum",
        "usd",
    ],
    [
        "https://api.bittrex.com/api/v1.1/public/getticker?market=USD-ETH",
        "result",
        "Last",
    ],
    ["https://api.gemini.com/v1/pubticker/ethusd", "last"],
    [
        "https://api.kraken.com/0/public/Ticker?pair=ETHUSDC",
        "result",
        "ETHUSDC",
        "c",
        0,
    ],
]

# btc, eth are helper dictionaries used to distinguish btc prices and eth prices
# these are used for data wrangling, from centralized API endpoints to medianization

btc = {
    "requestId": 0,
    "price": 0,
    "strPrice": "",
    "asset": "BTCUSD",
    "timestamp": 0,
    "lastPushedPrice": 0,
    "timeLastPushed": 0,
}
eth = {
    "requestId": 1,
    "price": 0,
    "asset": "ETHUSD",
    "strPrice": "",
    "timestamp": 0,
    "lastPushedPrice": 0,
    "timeLastPushed": 0,
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
    """
    Fetches price data from centralized public web API endpoints
    Returns: (str) ticker price from public exchange web APIs
    Input: (list of str) public api endpoint with any necessary json parsing keywords
    """
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
    except:
        response = 0
        print("API ERROR", public_api[0])


def getAPIValues():

    btc["timestamp"] = int(time.time())
    price = medianize(btcAPIs)
    btc["strPrice"] = str(price)
    btc["price"] = int(price * (10 ** 18))
    eth["timestamp"] = int(time.time())
    price = medianize(ethAPIs)
    eth["strPrice"] = str(price)
    eth["price"] = int(price * (10 ** 18))
    return [btc, eth]


def medianize(_apis):
    """
    Medianizes price of an asset from a selection of centralized price APIs
    """
    finalRes = []
    didGet = False
    n = 0
    for i in _apis:
        _res = fetchAPI(i)
        if not _res:
            continue
        if _res > 0:
            didGet = True
            finalRes.append(_res)

    # sort final results
    finalRes.sort()
    return finalRes[int(len(finalRes) / 2)]


def TellorSignerMain():
    while True:
        nonce = w3.eth.get_transaction_count(
            "0xfa30C73618d5b34Cb30F17C1874cd426Da4C0668"
        )
        assets = getAPIValues()
        for asset in assets:
            if (
                asset["timestamp"] - asset["timeLastPushed"] > 5
                or abs(asset["price"] - asset["lastPushedPrice"]) > 0.05
            ):
                tx = tellor_playground.functions.submitValue(
                    asset["requestId"], asset["price"]
                ).buildTransaction(
                    {
                        "chainId": 4,
                        "nonce": nonce,
                        "gas": 400000,
                        "gasPrice": w3.toWei("2", "gwei"),
                    }
                )
                tx_signed = w3.eth.default_account.sign_transaction(tx)
                try:
                    w3.eth.send_raw_transaction(tx_signed.rawTransaction)
                except:
                    print(
                        f"""Warning: tx may have sent with wrong nonce.
                    \nCheck https://rinkeby.etherscan.io/address/{acc.address}"""
                    )

        time.sleep(0)
        print("waiting to submit....")


TellorSignerMain()
