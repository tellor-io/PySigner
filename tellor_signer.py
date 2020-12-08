
from stark_cli import sign_cli,hash_price,public_cli
import time,requests,json,hashlib,os
from web3 import Web3
from eth_account.messages import encode_defunct
from web3.auto import w3
from bitstring import BitArray
from signature import pedersen_hash
from dotenv import load_dotenv

load_dotenv()


privateKey = os.getenv("PRIVATEKEY")
myName = "TRB"
submissionURL = "http://api.stage.dydx.exchange/v3/price"
btcAPIs = ["json(https://api.pro.coinbase.com/products/BTC-USD/ticker).price",
		"json(https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd).bitcoin.usd"]
ethAPIs = [		"json(https://api.pro.coinbase.com/products/ETH-USD/ticker).price",
		"json(https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd).ethereum.usd"]

btc = {
  "price":0,
  "asset":"BTC/USD",
  "timestamp": 0,
  "lastPushedPrice":0,
  "timeLastPushed":0
}
eth = {
  "price": 0,
  "asset":"ETH/USD",
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
	btc["price"] = int(medianize(btcAPIs)*(10**18))
	eth["timestamp"] = int(time.time())
	eth["price"] = int(medianize(ethAPIs)*(10**18))
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
	return int(float(price))


def signValue(data):
	starkKey = EthKeyToStarkKey(privateKey)
	intKey = int(starkKey,16)
	intData = int(data,16)
	x = sign_cli(intKey,intData)
	y = x.split(' ')
	submitData["signatureR"] = y[0]
	submitData["signatureS"] = y[1]

def formatData(data):
	n = Web3.toHex(str.encode(data["asset"]))
	c = bin(int(data["asset"].encode('utf-8').hex(),16))[:128]
	asset = hex(int(c, 2)).ljust(34,"0")
	asset =int(asset,16)
	name = int(myName.encode('utf-8').hex(),16)
	return hash_price(name,asset,data["price"],data["timestamp"])

def submitSignature(_signedData):
	print(_signedData)
	x = requests.post(submissionURL,data=_signedData)
	print(x)

def EthKeyToStarkKey(eth_key):
	message = encode_defunct(text="StarkKeyDerivation")
	eth_signature = w3.eth.account.sign_message(message, private_key=eth_key)
	ethSignatureHash = Web3.keccak(eth_signature.signature)
	c = bin(int(ethSignatureHash.hex(), base=16))[:251]
	stark_private_key = hex(int(c, 2))
	return stark_private_key

def TellorSignerMain():
	submitData["starkKey"] = public_cli(int(EthKeyToStarkKey(privateKey),16))
	submitData["oracleName"] = myName
	while True:
		assets = getAPIValues()
		for i in range(len(assets)):
			apiData = assets[i]
			data = formatData(apiData)
			signValue(data)
			if assets[i]["timestamp"]- assets[i]["timeLastPushed"] > 300 or abs(assets[i]["price"] - assets[i]["lastPushedPrice"]) > .02:
				submitData["assetName"] = assets[i]["asset"]
				submitData["price"] = assets[i]["price"]
				submitData["timestamp"] = assets[i]["timestamp"]
				print("submitting data :", submitData)
				submitSignature(submitData)
				assets[i]["lastPushedPrice"] = assets[i]["price"]
				assets[i]["timeLastPushed"] = assets[i]["timestamp"]
		time.sleep(10);
		print("....")

TellorSignerMain()
#print(medianize(btcAPIs))
#print(medianize(ethAPIs))
#print(public_cli(int(privateKey,16)))

#print(public_cli(int(EthKeyToStarkKey(privateKey),16)))

#Add   bitstamp
  # bittrex
  # gemini
  # kraken

#curl -X POST --data '{"starkKey": "0x13ebb76f3d0c31448a84bcfca6edc246637f3f6d8aa5ab2cb7e030d5b7c9034", "timestamp": 1607454394, "price": 18839000000000000000000, "assetName":"BTC-USD", "oracleName":"Tellor", "signatureR": "0x26eba72c3328edc5f4897979bff80a1d8325c6acf1823c6fa5be21804d9ba67", "signatureS": "0x3e43b9d54e626f8d17bb24d3b89b1b00e43b192ec844a1561d74f78bf2b35e0"}' https://api.stage.dydx.exchange/v3/price

