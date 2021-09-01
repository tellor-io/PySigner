import argparse
import json
import os

import telebot
from dotenv import find_dotenv
from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import geth_poa_middleware

load_dotenv(find_dotenv())

with open("config.json") as f:
    config = json.loads(f.read())[0]

with open("TellorMesosphere.json") as f:
    abi = f.read()


# Building CLI interface
parser = argparse.ArgumentParser(description="Submit values to Tellor Mesosphere")
parser.add_argument(
    "-n",
    "--network",
    nargs=1,
    required=True,
    type=str,
    help="an EVM compatible network",
)
args = parser.parse_args()
network = args.network[0]

node = config["networks"][network]["node"]
explorer = config["networks"][network]["explorer"]
chainId = config["networks"][network]["chainId"]

contract_address = config["address"]

bot = telebot.TeleBot(os.getenv("TG_TOKEN"), parse_mode=None)
private_key = os.getenv("PRIVATEKEY")
myName = "Tellor"
w3 = Web3(Web3.HTTPProvider(node))

# Choose network from CLI flag
if network == "rinkeby" or network == "mumbai" or network == "rinkeby-arbitrum":
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
mesosphere = w3.eth.contract(Web3.toChecksumAddress(contract_address), abi=abi)

acc = w3.eth.default_account = w3.eth.account.from_key(private_key)
precision = 1e6

print("your address:", acc.address)
print("your balance:", w3.eth.get_balance(acc.address))
