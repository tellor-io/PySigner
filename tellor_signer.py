
from stark_cli import sign_cli,hash_price
import time 
from web3 import Web3

apiString =  'json(https://api.gdax.com/products/BTC-USD/ticker).price'
privateKey = "0x000000001"

def getAPIValues():
	apiVals = []
	btc = {
	  "oracle": "TRB",
	  "price": 1,
	  "asset":"BTC/USD",
	  "timestamp":int(time.time())
	}
	eth = {
	  "oracle": "TRB",
	  "price": 2,
	  "asset":"ETH/USD",
	  "timestamp": int(time.time())
	}
	return [btc,eth]

def signValue(data):
	return sign_cli(privateKey,data)

def formatData(data):
	n = Web3.toHex(str.encode(data["oracle"]))
	name =int(n,16)
	n = Web3.toHex(str.encode(data["asset"]))
	asset =int(n,16)
	return hash_price(name,asset,data["price"],data["timestamp"])

def submitSignature():
	pass

def TellorSignerMain():
	while True:
		assets = getAPIValues()
		for i in range(len(assets)):
			apiData = assets[i]
			data = formatData(apiData)
			signedData = signValue(data)
			# submitSignature(signedData)
		break
		time.sleep(60);


TellorSignerMain()