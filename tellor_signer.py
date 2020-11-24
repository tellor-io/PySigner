
from stark_cli import sign_cli,hash_price
import time,requests,json
from web3 import Web3

apiString =  'json(https://api.gdax.com/products/BTC-USD/ticker).price'
privateKey = "0x000000001"

btcAPIs = ["json(https://api.pro.coinbase.com/products/BTC-USD/ticker).price",
		"json(https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd).bitcoin.usd"]
ethAPIs = [		"json(https://api.pro.coinbase.com/products/ETH-USD/ticker).price",
		"json(https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd).ethereum.usd"]

def getAPIValues():
	apiVals = []
	btc = {
	  "oracle": "TRB",
	  "price": medianize(btcAPIs),
	  "asset":"BTC/USD",
	  "timestamp":int(time.time())
	}
	eth = {
	  "oracle": "TRB",
	  "price": medianize(ethAPIs),
	  "asset":"ETH/USD",
	  "timestamp": int(time.time())
	}
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
	intKey = int(privateKey,16)
	intData = int(data,16)
	return sign_cli(intKey,intData)

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
			print(signedData)
			# submitSignature(signedData)
		break
		time.sleep(60);


TellorSignerMain()
#print(medianize(btcAPIs))
#print(medianize(ethAPIs))