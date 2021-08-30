import sys

from pysigner.mesosphere_signer import TellorSigner, get_configs

def run_signer():
    cfg = get_configs(sys.argv[1:])
    signer = TellorSigner(cfg)
    signer.run()