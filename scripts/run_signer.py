import sys

from pysigner.mesosphere_signer import get_configs
from pysigner.mesosphere_signer import TellorSigner


def run_signer(private_key):
    cfg = get_configs(sys.argv[1:])
    signer = TellorSigner(cfg, private_key)
    signer.run()
