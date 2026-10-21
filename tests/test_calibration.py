"""Puerta de calibracion (Fase 2). Necesita data/bitstamp_*.csv (python -m sqzlab.fetch --source bitstamp ...)."""
import pytest

from sqzlab.calibrate import run_all
from sqzlab.fetch import path_for

pytestmark = pytest.mark.skipif(not path_for("bitstamp", "BTC", "4h").exists(), reason="faltan datos de Bitstamp")


@pytest.fixture(scope="module")
def calib():
    return run_all()


def test_btc_4h_matches_tradingview(calib):
    tab, spots = calib
    r = tab.set_index("base").loc["BTC 4h"]
    assert r.port_trades == r.tv_trades and r.port_wins == r.tv_wins
    assert abs(r.port_pnl - r.tv_pnl) / r.tv_pnl < 0.01
    assert abs(r.port_pf - r.tv_pf) < 0.01
    assert all(x["ok"] for x in spots["BTC 4h"])


def test_btc_1d_recent_trades_match_exactly(calib):
    _, spots = calib
    assert all(x["ok"] for x in spots["BTC 1D"])


def test_eth_1w_matches(calib):
    r = calib[0].set_index("base").loc["ETH 1W"]
    assert r.port_trades == r.tv_trades and abs(r.port_pnl - r.tv_pnl) < 1.0
