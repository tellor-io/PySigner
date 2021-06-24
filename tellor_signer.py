
from stark_cli import sign_cli,hash_price,public_cli
import time,requests,json,hashlib,os
from web3 import Web3
from eth_account.messages import encode_defunct
from web3.auto import w3
from bitstring import BitArray
from signature import pedersen_hash
from dotenv import load_dotenv,find_dotenv

load_dotenv(find_dotenv())


privateKey = os.getenv("PRIVATEKEY")
myName = "Tello"
submissionURL = "https://api.stage.dydx.exchange/v3/price"

# BTC and ETH api endpoints from centralized exchanges
# Each endpoint is encased in a list with the keywords that parse the JSON to the last price

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

# btc, eth are helper dictionaries used to distinguish btc prices and eth prices
# these are used for data wrangling, from centralized API endpoints to medianization

btc = {
  "price":0,
  "strPrice":"",
  "asset":"BTCUSD",
  "timestamp": 0,
  "lastPushedPrice":0,
  "timeLastPushed":0
}
eth = {
  "price": 0,
  "asset":"ETHUSD",
  "strPrice":"",
  "timestamp": 0,
  "lastPushedPrice":0,
  "timeLastPushed":0
}

#final data submission format

submitData = {
	"starkKey":0,
	"timestamp":0,
	"price":0,
	"assetName":0, #btc or eth
	"oracleName":0,
	"signatureR":0,
	"signatureS":0
}

def getAPIValues():
	'''Formats values into approrpriate data types and adds them to btc or eth helper dict'''
	btc["timestamp"] = int(time.time())
	price = medianize(btcAPIs)
	btc["strPrice"] = str(price)
	btc["price"] = int(price*(10**18))
	eth["timestamp"] = int(time.time())
	price = medianize(ethAPIs)
	eth["strPrice"] =str(price)
	eth["price"] = int(price*(10**18))
	return [btc,eth]

def medianize(_apis):
	'''
	Medianizes price of an asset from a selection of centralized price APIs
	'''
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
	
	#sort final results
	finalRes.sort()

	#return median element
	return finalRes[int(len(finalRes)/2)]

def fetchAPI(public_api):
	''' 
	Fetches price data from centralized public web API endpoints
	Returns: (str) ticker price from public exchange web APIs
	Input: (list of str) public api endpoint with any necessary json parsing keywords
	'''
	try:
		#Parse list input
		endpoint = public_api[0]
		parsers = public_api[1:]

		#Request JSON from public api endpoint
		r = requests.get(endpoint)
		json_ = r.json()
		
		#Parse through json with pre-written keywords
		for keyword in parsers:
			json_ = json_[keyword]

		#return price (last remaining element of the json)
		price = json_
		return float(price)
	except:
		response = 0
		print('API ERROR', public_api[0])


def signValue(data):
	'''Sign values with Stark Key'''
	starkKey = EthKeyToStarkKey(privateKey)
	intKey = int(starkKey,16)
	intData = int(data,16)
	x = sign_cli(intKey,intData)
	y = x.split(' ')
	submitData["signatureR"] = str(y[0])
	submitData["signatureS"] = str(y[1])

def formatData(data):
	'''Format data with appropriate data types'''
	n = Web3.toHex(str.encode(data["asset"]))
	c = bin(int(data["asset"].encode('utf-8').hex(),16))[:128]
	asset = hex(int(c, 2)).ljust(34,"0")
	asset =int(asset,16)
	name = myName.encode('utf-8').hex()
	return hash_price(int(name,16),asset,data["price"],data["timestamp"])

def submitSignature():
	'''Helper function for printing/submitting data'''
	current_time = time.strftime("%H:%M", time.localtime(time.time()))
	print(str(current_time)," | ",submitData)
	headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
	print(requests.post(submissionURL,data=json.dumps(submitData),headers=headers))

def EthKeyToStarkKey(eth_key):
	'''Convert eth message signature to Stark Key signature with keccak'''
	message = encode_defunct(text="StarkKeyDerivation")
	eth_signature = w3.eth.account.sign_message(message, private_key=eth_key)
	ethSignatureHash = Web3.keccak(eth_signature.signature)
	c = bin(int(ethSignatureHash.hex(), base=16))[:251]
	stark_private_key = hex(int(c, 2))
	return stark_private_key

def TellorSignerMain():
	'''Submit price if last price submission was 5 minutes ago or if price deviates by 5 percent'''
	submitData["starkKey"] = str(public_cli(int(EthKeyToStarkKey(privateKey),16)))
	submitData["oracleName"] = str(myName)
	while True:
		assets = getAPIValues()
		for i in range(len(assets)):
			apiData = assets[i]
			data = formatData(apiData)
			signValue(data)
			if assets[i]["timestamp"]- assets[i]["timeLastPushed"] > 300 or abs(assets[i]["price"] - assets[i]["lastPushedPrice"]) > .05:
				submitData["assetName"] = assets[i]["asset"]
				submitData["price"] = assets[i]["strPrice"]
				submitData["timestamp"] = assets[i]["timestamp"]
				submitSignature()
				assets[i]["lastPushedPrice"] = assets[i]["price"]
				assets[i]["timeLastPushed"] = assets[i]["timestamp"]
		time.sleep(10)
		print("....")

def testSubmit():
	data = {'starkKey': '0x13ebb76f3d0c31448a84bcfca6edc246637f3f6d8aa5ab2cb7e030d5b7c9034', 'timestamp': 1607520077, 'price': '561.77', 'assetName': 'ETHUSD', 'oracleName': 'Tellor', 'signatureR': '0x46b6c32b6425b78661e0b017b290dd21893b0df1bbfd5045cc19e878a7ba832', 'signatureS': '0x6527f39fae6ce2a6ea7ada31f4ec91f33ab574178a1c0fc805332795f62e79f'}
	print(json.dumps(data))
	headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
	print(requests.post(submissionURL,data=json.dumps(data),headers=headers))

TellorSignerMain()
