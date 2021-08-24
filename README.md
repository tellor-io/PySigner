# PySigner

A python library + script for requesting, standardizing, and signing price feeds.

## Setup and Usage

### Set up environment

[Python 3.8](https://www.python.org/downloads/release/python-380/) or higher is required, as is pipenv. Installation instructions for `pipenv` are [here](https://pipenv.pypa.io/en/latest/install/#pragmatic-installation-of-pipenv), if not preinstalled.

Clone the repository and install python dependencies:

```
git clone https://github.com/tellor-io/PySigner.git
cd ./Pysigner && pipenv install
```

### Change environment variables

TellorSigner reads api keys and other user secrets from a `.env` file. Rename `.env.example` to `.env` and update the variables as follows:
- `PRIVATEKEY` is your ETH private key.
- `INFURA_KEY` is needed if testing on a network like rinkeby. Sign up for infura [here](https://infura.io/).
- `TG_TOKEN` and `CHAT_ID` are needed if you want to receive error alerts to a Telegram chat group. Instructions for getting these strings are [here]().
- `BOT_NAME` can be specified if using Telegram alerts.
- `TEST_VAR` is for testing. Don't change it.

### Usage

```
pipenv run python ./pysigner/mesosphere_signer.py
```

### Configuring the signer

`config.yml`

### Testing

```
pipenv shell
cd ./tests
pytest
```

### Formatting
```
pipenv shell
cd ./pysigner
black ./
```