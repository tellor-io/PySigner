# PySigner

`pysigner` is a python package for requesting, standardizing, and signing price feeds.

## Setup and Usage

### Set up environment

[Python 3.8](https://www.python.org/downloads/release/python-380/) or higher is required, as is [pipenv](https://pipenv.pypa.io/en/latest/install/#pragmatic-installation-of-pipenv).

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
The main script for signing price data can be run with:
```
pipenv run python ./pysigner/mesosphere_signer.py
```
To run the script continuously in the background, you can use a linux [AWS instance](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/EC2_GetStarted.html) and the built in [screen](https://ss64.com/bash/screen.html) utility.

Once connected to an EC2 instance, run the following in this repository's home directory:
```
pipenv shell
cd ./pysigner
screen
python mesosphere_signer.py
```

Once the script is running, detach the screen session by pressing `Ctrl+A` then `D`. You can now close your connection to the AWS instance and the signer will continue to run.

Verify transactions sent on the polygon network [here](https://polygonscan.com/txs?a=0xACC2d27400029904919ea54fFc0b18Bf07C57875&p=1).

### Configuring TellorSigner
Most settings for the signer are located in `config.yml`. `network`, `gasprice`, and `receipt_timeout` are some commonly adjusted parameters.

### Testing
Test `pysigner` package using [pytest](https://docs.pytest.org/en/6.2.x/). Navigate to `./tests` and run:

```
pytest
```

### Formatting
Please format contributions to this project using [black](https://github.com/psf/black). For example, formatting all python files in `./pysigner` looks like:
```
cd ./pysigner
black ./
```
