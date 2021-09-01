from pysigner.mesosphere_signer import (
    Asset,
    get_configs,
    get_price,
    medianize,
    medianize_eth_dai,
    medianize_prices,
    TellorSigner,
)


def test_asset():
    ass = Asset("TRB", 1)
    assert ass.name == "TRB"
    assert ass.request_id == 1


def test_read_config_file():
    cfg = get_configs([])

    assert type(cfg.network) == str
    assert cfg.network in ("rinkeby", "mumbai", "polygon")

    assert type(cfg.precision) == int
    assert cfg.precision == 1e6

    assert type(cfg.gasprice) == str
    assert cfg.gasprice.replace(".", "", 1).isdigit()  # can be cast as int/float

    assert type(cfg.error_gasprice) == float
    assert type(cfg.extra_gasprice_ceiling) == float
    assert type(cfg.error_waittime) == int

    assert cfg.address.polygon == "0xACC2d27400029904919ea54fFc0b18Bf07C57875"  # tellor contract


def test_get_cl_config_args():
    cfg = get_configs(["-n", "narya", "-gp", "42", "-egp", "100."])

    assert cfg.network == "narya"
    assert cfg.gasprice == "42"
    assert cfg.error_gasprice == 100.0


def test_price_apis():
    cfg = get_configs([])

    for asset in cfg.apis:
        for name in cfg.apis[asset]:

            price = get_price(cfg.apis[asset][name])
            assert price != None
            assert price > 0


def test_medianize_eth_dai():
    cfg = get_configs([])
    eth_dai_price = medianize_eth_dai(cfg.apis.ETHUSD, cfg.apis.DAIUSD, cfg.precision)

    assert type(eth_dai_price) == int
    assert eth_dai_price > 0


def test_medianize_prices():
    cfg = get_configs([])
    wbtc_price = medianize_prices(cfg.apis.WBTCUSD, cfg.precision)

    assert type(wbtc_price) == int
    assert wbtc_price > 0


def test_medianize():
    assert 1.0 == medianize([0.0, 1.0, 2.0])
    assert 2.0 == medianize([1.0, 2.0])
    assert 1.0 == medianize([1.0])


def test_create_signer_instance():

    def create_signer_on_network(network, contract_address):
        cfg = get_configs(["-n", network])
        signer = TellorSigner(cfg)
        network = cfg["network"]

        assert (
            signer.cfg.address[network] == contract_address
        )  # tellor contract
        assert signer.w3.isConnected() == True
        assert signer.secret_test == "passed"
        assert signer.acc.address != None
        assert signer.acc.address != ""

    create_signer_on_network("polygon", "0xACC2d27400029904919ea54fFc0b18Bf07C57875")
    create_signer_on_network("rinkeby", "0xAE50BA0d54610898e078EE0D39dB0a7654968551")


def test_build_tx():
    # build single tx
    pass


def test_send_tx():
    # send single tx
    pass
