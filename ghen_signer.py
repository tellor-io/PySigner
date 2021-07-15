import argparse, time, json, requests, os

from dotenv import load_dotenv, find_dotenv
import telebot
from web3 import Web3
from web3.middleware import geth_poa_middleware

load_dotenv(find_dotenv())

with open('abi.json') as f:
	abi = f.read()
	f.close()

with open('config.json') as f:
	config = json.loads(f.read())[0]
	f.close()

with open('TellorMesosphere.json') as f:
	abi = f.read()


#Building CLI interface
parser = argparse.ArgumentParser(description='Submit values to Tellor Mesosphere')
parser.add_argument('-n', '--network', nargs=1, required=True, type=str, help="an EVM compatible network")
args = parser.parse_args()
network = args.network[0]

node = config['networks'][network]['node']
if network == "rinkeby" or network == "mainnet":
	node += os.getenv('INFURA_KEY')
explorer = config['networks'][network]['explorer']
chainId = config['networks'][network]['chainId']

contract_address = config['address']

bot = telebot.TeleBot(os.getenv("TG_TOKEN"), parse_mode=None)
private_key = os.getenv("PRIVATEKEY")
myName = "Tellor"
w3 = Web3(Web3.HTTPProvider(node))

#Choose network from CLI flag
if network == "rinkeby" or network == "mumbai" or network == "rinkeby-arbitrum":
	w3.middleware_onion.inject(geth_poa_middleware, layer=0)
mesosphere = w3.eth.contract(
	Web3.toChecksumAddress(contract_address),
	abi = abi
)

acc = w3.eth.default_account = w3.eth.account.from_key(private_key)
precision = 1e6

print('your address', acc.address)
print('your balance', w3.eth.get_balance(acc.address))
# BTC and ETH api endpoints from centralized exchanges
# Each endpoint is encased in a list with the keywords that parse the JSON to the last price

ethAPIs = ['https://thegraph.com/legacy-explorer/subgraph/zippoxer/sushiswap-subgraph-fork', #api endpoint
	'data', 'pair', 'token0price'] #parsers

daiAPIs = [
]

# btc, eth are helper dictionaries used to distinguish btc prices and eth prices
# these are used for data wrangling, from centralized API endpoints to medianization

eth = {
  "requestId":1,
  "price": 0,
  "asset":"ETHUSD",
  "strPrice":"",
  "timestamp": 0,
  "lastPushedPrice":0,
  "timeLastPushed":0
}


#final data submission format

submitData = {
	# "starkKey":0,
	"timestamp":0,
	"price":0,
	"assetName":0, #btc or eth
	"oracleName":0,
	# "signatureR":0,
	# "signatureS":0
}

def fetchAPI(public_api):
	''' 
	Fetches price data from centralized public web API endpoints
	Returns: (str) ticker price from public exchange web APIs
	Input: (list of str) public api endpoint with any necessary json parsing keywords
	'''
	
	r = requests.post('https://api.thegraph.com/subgraphs/name/zippoxer/sushiswap-subgraph-fork',json={'query':'''
		{
		pair(id: "0x397ff1542f962076d0bfe58ea045ffa2d347aca0") {
			id
			token0 {
			id,
			symbol
			}
			token1 {
			id,
			symbol
			}
			token0Price
			token1Price
		}
		}

		'''}).json()['data']['pair']['token0Price']

	return float(r)

def getAPIValues():

	eth["timestamp"] = int(time.time())
	price = fetchAPI(ethAPIs)
	eth["strPrice"] =str(price)
	eth["price"] = int(price*(precision))


	return [eth]

def TellorSignerMain():
	while True:
		alert_sent = False
		assets = getAPIValues()
		for asset in assets:
			nonce = w3.eth.get_transaction_count(acc.address)
			print(nonce)
			#if signer balance is less than half an ether, send alert
			if (w3.eth.get_balance(acc.address) < 5E14) and ~alert_sent:
				bot.send_message(os.getenv("CHAT_ID"), f'''warning: signer balance now below .5 ETH
				\nCheck {explorer}/address/'''+ acc.address)
				alert_sent = True
			else:
				alert_sent = False
			if (asset["timestamp"] - asset["timeLastPushed"] > 5) or (abs(asset["price"] - asset["lastPushedPrice"]) > .05):
				tx = mesosphere.functions.submitValue(asset['requestId'], asset['price']).buildTransaction(
					{
						'nonce': nonce,
						'gas': 4000000,
						'gasPrice': w3.toWei('3', 'gwei'),
						'chainId':chainId
					}
				)
				tx_signed = w3.eth.default_account.sign_transaction(tx)
				try:
					w3.eth.send_raw_transaction(tx_signed.rawTransaction)
					print(asset['asset'])
					print(asset['price'])

					asset["lastPushedPrice"] = asset["price"]
					asset["timeLastPushed"] = asset["timestamp"]
					# nonce += 1
					print("waiting to submit....")
					time.sleep(5)
				except:
					nonce += 1
					if w3.eth.get_balance(acc.address) < 0.005*1E18:
						bot.send_message(os.getenv("CHAT_ID"), f'''urgent: signer ran out out of ETH"
						\nCheck {explorer}/address/{acc.address}''')
						time.sleep(60*15)


TellorSignerMain()