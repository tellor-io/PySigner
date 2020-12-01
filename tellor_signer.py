
from stark_cli import sign_cli,hash_price,public_cli
import time,requests,json,hashlib
from web3 import Web3
from eth_account.messages import encode_defunct
from web3.auto import w3
from bitstring import BitArray

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
	intKey = int(privateKey,16)
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

def EthKeyToStarkKey():
	pass
#TellorSignerMain()
#print(medianize(btcAPIs))
#print(medianize(ethAPIs))
#print(public_cli(int(privateKey,16)))

def to_32byte_hex(val):
	return Web3.toHex(Web3.toBytes(val).rjust(32, b'\0'))

def testSign():
	eth_key = 0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d
	eth_address = "0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1"
	message = encode_defunct(text="StarkKeyDerivation")
	eth_signature = w3.eth.account.sign_message(message, private_key=eth_key)
	ethSignatureHash = Web3.keccak(eth_signature.signature)
	print(ethSignatureHash.hex())
	c = bin(int(ethSignatureHash.hex(), base=16))[:251]
	stark_private_key = hex(int(c, 2))
	stark_key = public_cli(int(stark_private_key,16))
	# stark_key = public_cli(starkPrivateKey) =
	#   0x1895a6a77ae14e7987b9cb51329a5adfb17bd8e7c638f92d6892d76e51cebcf
	# ///////
	# timestamp = January 1st, 2020 = hex(1577836800) = 0x5e0be100
	# price = $11512.34 = hex(11512.34 * (10**18)) = 0x27015cfcb0230820000
	# asset_name = 128bits(hex("BTCUSD")) = 0x42544355534400000000000000000000
	# oracle_name = hex("Maker") = 0x4d616b6572
	# first_number = 0(84-bit) || AssetName (128-bit) || oracleName (40-bit) =
	#   425443555344000000000000000000004d616b6572
	# second_number = 0(100-bit) || Price(120-bit) || Timestamp (32-bit) =
	#   27015cfcb02308200005e0be100
	# data_hash = pedersen(first_number, second_number) =
 #  	3e4113feb6c403cb0c954e5c09d239bf88fedb075220270f44173ac3cd41858

 #  	//////
 #  	signature = StarkSign(key=stark_private_key, data=data_hash) =
	#   0x6a7a118a6fa508c4f0eb77ea0efbc8d48a64d4a570d93f5c61cd886877cb920
	#   0x6de9006a7bbf610d583d514951c98d15b1a0f6c78846986491d2c8ca049fd55

testSign()