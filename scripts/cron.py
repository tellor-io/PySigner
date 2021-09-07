import multiprocessing
import os
import sys
import traceback

from pysigner.mesosphere_signer import get_configs
from pysigner.mesosphere_signer import TellorSigner


def run_signer(private_key):
    """
    Starts mesosphere_signer.py with a provided private key
    """
    cfg = get_configs(sys.argv[1:])
    signer = TellorSigner(cfg, private_key)
    signer.run()


if __name__ == "__main__":
    for private_key in os.getenv("PRIVATEKEY").split(","):
        try:
            multiprocessing.Process(target=run_signer, args=(private_key,)).start()
        except multiprocessing.ProcessError as e:
            tb = str(traceback.format_exc())
            msg = str(e) + "\n" + tb
            print(msg)
