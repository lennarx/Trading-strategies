import pytest

from sqzlab import universe as U
from sqzlab.fetch import path_for


def test_fresh_groups_are_disjoint_from_used_coins_and_from_each_other():
    used = set(U.TRAIN) | set(U.HOLDOUT)
    assert not (set(U.FRESH_Z1) & used) and not (set(U.FRESH_Z2) & used) and not (set(U.FRESH_Z1) & set(U.FRESH_Z2))
    assert set(U.FRESH_Z1) | set(U.FRESH_Z2) == set(U.FRESH_CANDIDATES)   # sobrevivieron las 12


def test_partition_is_alphabetical_alternating():
    z1, z2 = U.partition_fresh(["DOT", "AAVE", "ATOM", "FIL"])
    assert z1 == ["AAVE", "DOT"] and z2 == ["ATOM", "FIL"]


@pytest.mark.skipif(not all(path_for("binance", s, "4h").exists() for s in U.FRESH_CANDIDATES), reason="faltan datos de Binance")
def test_hardcoded_groups_match_the_mechanical_rule():
    ok, dropped = U.screen_fresh()
    z1, z2 = U.partition_fresh(ok)
    assert not dropped and sorted(U.FRESH_Z1) == z1 and sorted(U.FRESH_Z2) == z2


def test_all_group_does_not_include_fresh_coins():
    assert set(U.load_universe.__defaults__) == {"all"}
    assert not (set(U.SOURCES) - set(U.TRAIN) - set(U.HOLDOUT) - set(U.FRESH_Z1) - set(U.FRESH_Z2))
