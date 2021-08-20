import json
import time
import traceback

import requests
import telebot

from state_variables import *


class Asset:
    def __init__(self, asset, requestId):
        self.asset = (asset,)
        self.requestId = (requestId,)
        self.price = (0,)
        self.string_price = ("0",)
        self.timestamp = (0,)
        self.last_pushed_price = (0,)
        self.time_last_pushed = 0

        self.api_list = []
        self.precision = 1e6

    def add_api_endpoint(self, api):
        self.api_list.append(api)

    def update_price(self):
        self.timestamp = int(time.time())
        self.price = int(self.medianize())

    def medianize(self):
        """
        Medianizes price of an asset from a selection of centralized price APIs
        """
        final_results = []
        didGet = False
        n = 0
        if not self.api_list:
            raise ValueError(
                "Cannot medianize prices of empty list. No APIs added for asset."
            )

        for api in self.api_list:
            price = self.fetch_api(api)
            final_results.append(price * self.precision)
        didGet = True

        # sort final results
        final_results.sort()
        return final_results[len(final_results) // 2]

    def fetch_api(self, api):
        """
        Fetches price data from centralized public web API endpoints
        Returns: (str) ticker price from public exchange web APIs
        Input: (list of str) public api endpoint with any necessary json parsing keywords
        """
        if not self.api_list:
            raise ValueError("No APIs added for asset.")
        try:
            # Parse list input
            endpoint = api.url
            parsers = api.request_parsers

            # Request JSON from public api endpoint
            r = requests.get(endpoint)
            json_ = r.json()

            # Parse through json with pre-written keywords
            for keyword in parsers:
                json_ = json_[keyword]

            # return price (last remaining element of the json)
            price = json_
            return float(price)
        except:
            response = r.status_code
            print("API ERROR", api.url, " ", response)


class API:
    def __init__(self, asset, url, request_parsers, subgraph=False):
        self.asset = (asset,)
        self.url = (url,)
        self.request_parsers = (request_parsers,)
        self.subgraph = subgraph


class Reporter:
    def __init__(self, account, tg_bot):
        self.account = account

    def submit_value(self, asset):
        alert_sent = False
        try:
            assets = asset.update_price()
        except:
            if not alert_sent:
                tb = traceback.format_exec()
                self.tg_bot.send_message(tb)
                alert_sent = True
        for asset in assets:
            try:
                nonce = w3.eth.get_transaction_count(acc.address)
                print(nonce)
                # if signer balance is less than half an ether, send alert
                if (w3.eth.get_balance(acc.address) < 5e14) and ~alert_sent:
                    bot.send_message(
                        os.getenv("CHAT_ID"),
                        f"""warning: signer balance now below .5 ETH
          \nCheck {explorer}/address/"""
                        + acc.address,
                    )
                    alert_sent = True
                else:
                    alert_sent = False
                if (asset["timestamp"] - asset["timeLastPushed"] > 5) or (
                    abs(asset["price"] - asset["lastPushedPrice"]) > 0.05
                ):
                    tx = mesosphere.functions.submitValue(
                        asset["requestId"], asset["price"]
                    ).buildTransaction(
                        {
                            "nonce": nonce,
                            "gas": 4000000,
                            "gasPrice": w3.toWei("3", "gwei"),
                            "chainId": chainId,
                        }
                    )
                    tx_signed = w3.eth.default_account.sign_transaction(tx)
            except:
                if not alert_sent:
                    traceback = traceback.format_exec()
                    bot.send_message(traceback)
                    alert_sent = True
                try:
                    w3.eth.send_raw_transaction(tx_signed.rawTransaction)
                    print(asset["asset"])
                    print(asset["price"])

                    asset["lastPushedPrice"] = asset["price"]
                    asset["timeLastPushed"] = asset["timestamp"]
                    # nonce += 1
                    print("waiting to submit....")
                    time.sleep(5)
                except:
                    nonce += 1
                    if w3.eth.get_balance(acc.address) < 0.005 * 1e18:
                        bot.send_message(
                            os.getenv("CHAT_ID"),
                            f"""urgent: signer ran out out of ETH"
            \nCheck {explorer}/address/{acc.address}""",
                        )
                        time.sleep(60 * 15)
