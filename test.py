import stark_cli
import time,requests,json,hashlib
from web3 import Web3
from eth_account.messages import encode_defunct
from web3.auto import w3
from signature import pedersen_hash
from decouple import config

def EthKeyToStarkKey(eth_key):
	message = encode_defunct(text="StarkKeyDerivation")
	eth_signature = w3.eth.account.sign_message(message, private_key=eth_key)
	ethSignatureHash = Web3.keccak(eth_signature.signature)
	c = bin(int(ethSignatureHash.hex(), base=16))[:251]
	stark_private_key = hex(int(c, 2))
	return stark_private_key

def testSign():
	time_string = "1 January, 2020"
	price = 11512.34
	asset = "BTCUSD"
	oracle_name = "Maker"


	time_res = time.strptime(time_string, "%d %B, %Y")
	timestamp = hex(int(time.mktime(time_res))-60*60*5)
	price = int(price*(10**18))
	price = 11512340000000000000000
	c = bin(int(asset.encode('utf-8').hex(),16))[:128]
	asset_name = hex(int(c, 2)).ljust(34,"0")
	oracle_name = oracle_name.encode('utf-8').hex()
	data_hash = stark_cli.hash_price(int(oracle_name,16),int(asset_name,16),price,int(timestamp,16))
	print(data_hash)
	#should be : 3e4113feb6c403cb0c954e5c09d239bf88fedb075220270f44173ac3cd41858
	myKey = EthKeyToStarkKey(config('PRIVATEKEY'))
	intKey = int(myKey,16)
	signature = stark_cli.sign_cli(intKey,int(data_hash,16))
	print(signature)

testSign()