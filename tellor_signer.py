
from stark_cli import sign_cli,hash_price,public_cli
import time,requests,json,hashlib
from web3 import Web3
from eth_account.messages import encode_defunct
from web3.auto import w3
from bitstring import BitArray
from signature import pedersen_hash

privateKey = "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"
submissionURL = "https://api.stage.dydx.exchange/v3/price"
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
	starkKey = EthKeyToStarkKey(privateKey)
	intKey = int(starkKey,16)
	intData = int(data,16)
	return sign_cli(intKey,intData)

def formatData(data):
	n = Web3.toHex(str.encode(data["oracle"]))
	name =int(n,16)
	n = Web3.toHex(str.encode(data["asset"]))
	asset =int(n,16)
	return hash_price(name,asset,data["price"],data["timestamp"])

def submitSignature(_signedData):
	x = requests.post(submissionURL, data = _signedData)
	print(x)

def TellorSignerMain():
	while True:
		assets = getAPIValues()
		for i in range(len(assets)):
			apiData = assets[i]
			data = formatData(apiData)
			signedData = signValue(data)
			print(signedData)
			submitSignature(signedData)
		break
		time.sleep(60);

def EthKeyToStarkKey(eth_key):
	message = encode_defunct(text="StarkKeyDerivation")
	eth_signature = w3.eth.account.sign_message(message, private_key=eth_key)
	ethSignatureHash = Web3.keccak(eth_signature.signature)
	c = bin(int(ethSignatureHash.hex(), base=16))[:251]
	stark_private_key = hex(int(c, 2))
	return public_cli(int(stark_private_key,16))

#TellorSignerMain()
#print(medianize(btcAPIs))
#print(medianize(ethAPIs))
#print(public_cli(int(privateKey,16)))

def to_32byte_hex(val):
	return Web3.toHex(Web3.toBytes(val).rjust(32, b'\0'))


def testSign():
	time_string = "1 January, 2020"
	price = 11512.34
	asset = "BTCUSD"
	oracle_name ="Maker"
	time_res = time.strptime(time_string, "%d %B, %Y")
	timestamp = hex(int(time.mktime(time_res))-60*60*5)
	price = hex(int(price*(10**18)))
	c = bin(int(asset.encode('utf-8').hex(),16))[:128]
	asset_name = hex(int(c, 2)).ljust(32,"0")
	oracle_name = oracle_name.encode('utf-8').hex()
	first_number = (asset_name + oracle_name)[2:]
	second_number = (price + timestamp[2:])[2:]
	print(first_number,second_number)
	data_hash = pedersen_hash(int(first_number,16),int(second_number,16))
	print(data_hash)
	#should be : 3e4113feb6c403cb0c954e5c09d239bf88fedb075220270f44173ac3cd41858
	myKey = EthKeyToStarkKey(0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d)
	intKey = int(myKey,16)
	signature = sign_cli(intKey,data_hash)
	print(signature)
 #  	signature = StarkSign(key=stark_private_key, data=data_hash) =
	#   0x6a7a118a6fa508c4f0eb77ea0efbc8d48a64d4a570d93f5c61cd886877cb920
	#   0x6de9006a7bbf610d583d514951c98d15b1a0f6c78846986491d2c8ca049fd55

testSign()