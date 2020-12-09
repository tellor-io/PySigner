
from stark_cli import sign_cli,hash_price,public_cli
import time,requests,json,hashlib,os
from web3 import Web3
from eth_account.messages import encode_defunct
from web3.auto import w3
from bitstring import BitArray
from signature import pedersen_hash
from dotenv import load_dotenv
# import logging

# # These two lines enable debugging at httplib level (requests->urllib3->http.client)
# # You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
# # The only thing missing will be the response.body which is not logged.
# try:
#     import http.client as http_client
# except ImportError:
#     # Python 2
#     import httplib as http_client
# http_client.HTTPConnection.debuglevel = 1

# # You must initialize logging, otherwise you'll not see debug output.
# logging.basicConfig()
# logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("requests.packages.urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True


load_dotenv()


privateKey = os.getenv("PRIVATEKEY")
myName = "Tellor"
submissionURL = "https://api.stage.dydx.exchange/v3/price"
btcAPIs = ["json(https://api.pro.coinbase.com/products/BTC-USD/ticker).price",
		"json(https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd).bitcoin.usd"]
ethAPIs = [		"json(https://api.pro.coinbase.com/products/ETH-USD/ticker).price",
		"json(https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd).ethereum.usd"]

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

submitData = {
	"starkKey":0,
	"timestamp":0,
	"price":0,
	"assetName":0,
	"oracleName":0,
	"signatureR":0,
	"signatureS":0
}

def getAPIValues():
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
	finalRes = []
	didGet = False
	n = 0
	for i in _apis:
		_res = fetchAPI (i)
		if _res > 0:
			didGet = True
			finalRes.append(_res)
	return finalRes[int(len(finalRes)/2)]

def fetchAPI(_api):
	_api = _api.replace("'", "")
	json = _api.split('(')[0]
	if('json' in json):
		_api = _api.split('(')[1]
		filter = _api.split(').')[1]
	_api = _api.split(')')[0]
	try:
		response = requests.request("GET", _api)
	except:
		response = 0;
		print('API ERROR',_api)
	if('json' in json):
		if(len(filter)):
			numFils = filter.count('.') + 1
			price = response.json()
			for i in range(numFils):
				thisFilter =  filter.split('.')[i]
				price =price[thisFilter]
		else:
			price = response.json()
	else:
		price = response
	return float(price)


def signValue(data):
	starkKey = EthKeyToStarkKey(privateKey)
	intKey = int(starkKey,16)
	intData = int(data,16)
	x = sign_cli(intKey,intData)
	y = x.split(' ')
	submitData["signatureR"] = str(y[0])
	submitData["signatureS"] = str(y[1])

def formatData(data):
	n = Web3.toHex(str.encode(data["asset"]))
	c = bin(int(data["asset"].encode('utf-8').hex(),16))[:128]
	asset = hex(int(c, 2)).ljust(34,"0")
	asset =int(asset,16)
	name = bin(int(myName.encode('utf-8').hex(),16))[:40]
	return hash_price(int(hex(int(name,2)),16),asset,data["price"],data["timestamp"])

def submitSignature():
	print(submitData)
	headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
	print(requests.post(submissionURL,data=json.dumps(submitData),headers=headers))

def EthKeyToStarkKey(eth_key):
	message = encode_defunct(text="StarkKeyDerivation")
	eth_signature = w3.eth.account.sign_message(message, private_key=eth_key)
	ethSignatureHash = Web3.keccak(eth_signature.signature)
	c = bin(int(ethSignatureHash.hex(), base=16))[:251]
	stark_private_key = hex(int(c, 2))
	return stark_private_key

def TellorSignerMain():
	submitData["starkKey"] = str(public_cli(int(EthKeyToStarkKey(privateKey),16)))
	submitData["oracleName"] = str(myName)
	while True:
		assets = getAPIValues()
		for i in range(len(assets)):
			apiData = assets[i]
			data = formatData(apiData)
			signValue(data)
			if assets[i]["timestamp"]- assets[i]["timeLastPushed"] > 300 or abs(assets[i]["price"] - assets[i]["lastPushedPrice"]) > .02:
				submitData["assetName"] = assets[i]["asset"]
				submitData["price"] = assets[i]["strPrice"]
				submitData["timestamp"] = assets[i]["timestamp"]
				submitSignature()
				assets[i]["lastPushedPrice"] = assets[i]["price"]
				assets[i]["timeLastPushed"] = assets[i]["timestamp"]
		time.sleep(10);
		print("....")

def testSubmit():
	data = {'starkKey': '0x13ebb76f3d0c31448a84bcfca6edc246637f3f6d8aa5ab2cb7e030d5b7c9034', 'timestamp': 1607520077, 'price': '561.77', 'assetName': 'ETHUSD', 'oracleName': 'Tellor', 'signatureR': '0x46b6c32b6425b78661e0b017b290dd21893b0df1bbfd5045cc19e878a7ba832', 'signatureS': '0x6527f39fae6ce2a6ea7ada31f4ec91f33ab574178a1c0fc805332795f62e79f'}
	print(json.dumps(data))
	headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
	print(requests.post(submissionURL,data=json.dumps(data),headers=headers))

#testSubmit()
TellorSignerMain()
#print(medianize(btcAPIs))
#print(medianize(ethAPIs))
#print(public_cli(int(privateKey,16)))

#print(public_cli(int(EthKeyToStarkKey(privateKey),16)))

#Add   bitstamp
  # bittrex
  # gemini
  # kraken