
from pysigner.mesosphere_signer import Asset


def test_asset():
    ass = Asset('TRB', 1)
    assert ass.name == 'TRB'
    assert ass.request_id == 1

