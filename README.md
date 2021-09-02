# PySigner

`pysigner` is a python package for submitting prices to TellorMesosphere. PySigner requests, standardizises, and signs price feeds.

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
- `PRIVATEKEY` is your ETH private key(s). You can supply more than one.
- `POKT_POLYGON` is needed if submitting on polygon. Sign up for pokt [here](https://www.pokt.network/).
- `POKT_RINKEBY` is needed if submitting on rinkeby. Sign up for pokt [here](https://www.pokt.network/).
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
screen
pipenv run python -m scripts.cron
```

Once the script is running, detach the screen session by pressing `Ctrl+A` then `D`. You can now close your connection to the AWS instance and the signer will continue to run.

You can verify transactions on your network's block explorer.

### Configuring TellorSigner
Most settings for the signer are located in `config.yml`. `network`, `gasprice`, and `receipt_timeout` are some commonly adjusted parameters.

The network can also be passed as a flag on the command line. For example:
```
pipenv run python -m scripts.cron -n rinkeby
```
OR
```
pipenv run python -m scripts.cron --network rinkeby
```

### Testing
Test `pysigner` package using [pytest](https://docs.pytest.org/en/6.2.x/). Run the following from the top directory:

```
pipenv run pytest ./tests
```

### Contributing
Please format contributions to this project using [tox](https://tox.readthedocs.io/en/latest/). Our tox workflow integrates [black](https://black.readthedocs.io/en/stable/), [pytest](https://docs.pytest.org/en/6.2.x/) and [pre-commit](https://pre-commit.com/) For example, formatting all python files in `./pysigner` is as simple as running:
```
tox
```
