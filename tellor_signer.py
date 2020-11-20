
from stark_cli import sign_cli,hash_price
import datetime 


apiString =  'json(https://api.gdax.com/products/BTC-USD/ticker).price'
privateKey = "0x000000001"

def getAPIValues():
	apiVals = []
	btc = {
	  "oracle": "Tellor",
	  "price": 1,
	  "asset":"BTC/USD",
	  "timestamp":datetime.datetime.now() 
	}
	eth = {
	  "oracle": "Tellor",
	  "price": 2,
	  "asset":"ETH/USD",
	  "timestamp":datetime.datetime.now() 
	}
	return [btc,eth]

def signValue(data):
	return sign_cli(privateKey,data)

def formatData(data):
	print(data["oracle"])
	return hash_price(data["oracle"],data["price"],data["asset"],data["timestamp"])

def submitSignature():
	pass

def TellorSignerMain():
	while True:
		assets = getAPIValues()
		for i in range(len(assets)):
			apiData = assets[i]
			data = formatData(apiData)
			print(data)
			# signedData = signValue(data)
			# submitSignature(signedData)
		break
		time.sleep(60);


TellorSignerMain()