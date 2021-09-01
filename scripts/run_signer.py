import sys

from pysigner.mesosphere_signer import get_configs
from pysigner.mesosphere_signer import TellorSigner


def run_signer():
    cfg = get_configs(sys.argv[1:])
    signer = TellorSigner(cfg)
    signer.run()
