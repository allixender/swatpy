"""Extracting SWAT outputs (ReadOut) from synthetic output.rch/.sub/.hru files."""

import os

import numpy as np
import pytest

from swatpy import ReadOut

import make_fixtures as fx

YEARS = fx.PRINTED_YEARS
MONTHS = list(range(1, 13))


def monthly_expected(names, j, area):
    return [fx.out_value(j, area, y, m) for y in YEARS for m in MONTHS]


@pytest.mark.parametrize("iprint", ["month", 0])
def test_rch_monthly_drops_summary_rows(monthly_outputs, iprint):
    r = ReadOut.rchOutputManipulator(["FLOW_IN", "FLOW_OUT"], [1, 2], "skip", True, 0, monthly_outputs, iprint=iprint)
    for area in (1, 2):
        # FLOW_IN encodes year and month, FLOW_OUT area and month
        assert r.outValues["FLOW_IN"][area] == pytest.approx(monthly_expected(fx.RCH_NAMES, 0, area))
        assert r.outValues["FLOW_OUT"][area] == pytest.approx(monthly_expected(fx.RCH_NAMES, 1, area))
        assert fx.YEAR_ROW not in r.outValues["FLOW_OUT"][area]
        assert fx.AVERAGE_ROW not in r.outValues["FLOW_OUT"][area]
    assert r.areaSizes == {1: pytest.approx(10.0), 2: pytest.approx(15.0)}


@pytest.mark.parametrize("cls,names,areas", [
    (ReadOut.rchOutputManipulator, fx.RCH_NAMES, [1, 2]),
    (ReadOut.subOutputManipulator, fx.SUB_NAMES, [1, 2]),
    (ReadOut.hruOutputManipulator, fx.HRU_NAMES, [1, 2, 3]),
])
def test_all_columns_found_and_aligned(monthly_outputs, cls, names, areas):
    r = cls([], areas, "skip", True, 0, monthly_outputs, iprint="month")
    assert list(r.columns) == names
    r = cls(names, areas, "skip", True, 0, monthly_outputs, iprint="month")
    for j, name in enumerate(names):
        for area in areas:
            values = r.outValues[name][area]
            assert len(values) == 24
            assert values == pytest.approx(monthly_expected(names, j, area), rel=1e-3), (name, area)


def test_columns_after_wider_fields(monthly_outputs):
    # CHOLA (sub) and BACTP/BACTLP (hru) are one character wider than their header labels
    s = ReadOut.subOutputManipulator(["CHOLA", "TNO3"], [2], "skip", True, 0, monthly_outputs, iprint="month")
    assert s.outValues["CHOLA"][2][0] == pytest.approx(fx.out_value(fx.SUB_NAMES.index("CHOLA"), 2, 2002, 1))
    assert s.outValues["TNO3"][2][0] == pytest.approx(fx.out_value(fx.SUB_NAMES.index("TNO3"), 2, 2002, 1))
    h = ReadOut.hruOutputManipulator(["BACTLP", "LATQCNT"], [3], "skip", True, 0, monthly_outputs, iprint="month")
    assert h.outValues["LATQCNT"][3][-1] == pytest.approx(fx.out_value(fx.HRU_NAMES.index("LATQCNT"), 3, 2003, 12))


def test_daily_reduced_variable_selection(daily_outputs):
    r = ReadOut.rchOutputManipulator(["FLOW_OUT", "SED_OUT"], [2], "skip", True, 0, daily_outputs, iprint="day")
    assert list(r.columns) == fx.DAILY_RCH
    assert len(r.outValues["FLOW_OUT"][2]) == 365
    assert r.outValues["FLOW_OUT"][2][:3] == pytest.approx([2.001, 2.002, 2.003])
    assert r.outValues["SED_OUT"][2][0] == pytest.approx(fx.out_value(fx.RCH_NAMES.index("SED_OUT"), 2, 2002, 1))

    h = ReadOut.hruOutputManipulator(["ET", "SURQ_GEN"], [1, 3], "skip", True, 0, daily_outputs, iprint="day")
    assert list(h.columns) == fx.DAILY_HRU
    assert h.areaSizes == {1: pytest.approx(6.0), 3: pytest.approx(5.0)}
    assert h.outValues["SURQ_GEN"][3][100] == pytest.approx(fx.out_value(fx.HRU_NAMES.index("SURQ_GEN"), 3, 2002, 101))


def test_unknown_variable_raises(daily_outputs):
    with pytest.raises(KeyError, match="EVAP"):
        ReadOut.rchOutputManipulator(["EVAP"], [1], "skip", True, 0, daily_outputs, iprint="day")


def test_write_statistics_files(monthly_outputs, tmp_path):
    stats_dir = tmp_path / "stats"
    stats_dir.mkdir()
    ReadOut.subOutputManipulator(["SURQ"], [1, 2], "sum & indi", False, 0, monthly_outputs,
                                 iprint="month", stats_dir=str(stats_dir))
    written = sorted(os.listdir(stats_dir))
    assert written == ["SWAT_readout_SURQ_0001.sub", "SWAT_readout_SURQ_0001_statistics.sub",
                       "SWAT_readout_SURQ_0002.sub", "SWAT_readout_SURQ_0002_statistics.sub",
                       "SWAT_readout_SURQ_SUM.sub", "SWAT_readout_SURQ_SUMstatistics.sub"]
    values = np.loadtxt(stats_dir / "SWAT_readout_SURQ_0001.sub")
    assert values == pytest.approx([fx.out_value(fx.SUB_NAMES.index("SURQ"), 1, 2002, 1)] * 24, rel=1e-3)
    mean, median, var = np.loadtxt(stats_dir / "SWAT_readout_SURQ_SUMstatistics.sub")
    surq = fx.out_value(fx.SUB_NAMES.index("SURQ"), 1, 2002, 1) * 10.0 + fx.out_value(fx.SUB_NAMES.index("SURQ"), 2, 2002, 1) * 15.0
    assert mean == pytest.approx(surq * 1000.0 / 24 / 60 / 60, rel=1e-3)


def write_observed(path, values, nodata_at=()):
    with open(path, "w") as f:
        for i, v in enumerate(values):
            v = -9999 if i in nodata_at else v
            f.write("%d;FLOW_OUT_%d;%s\n" % (i + 1, i + 1, v))


def test_efficiency_perfect_fit(monthly_outputs, tmp_path):
    observed = tmp_path / "obs.txt"
    write_observed(observed, monthly_expected(fx.RCH_NAMES, 1, 1))
    e = ReadOut.efficiency("FLOW_OUT", 1, str(observed), 3, 0, monthly_outputs, iprint="month")
    assert len(e.outValues) == len(e.obs) == 24
    assert e.nash() == pytest.approx(1.0)
    assert e.agr() == pytest.approx(1.0)


def test_efficiency_masks_nodata(monthly_outputs, tmp_path):
    observed = tmp_path / "obs.txt"
    sim = monthly_expected(fx.RCH_NAMES, 1, 1)
    write_observed(observed, sim, nodata_at=(3, 7))
    e = ReadOut.efficiency("FLOW_OUT", 1, str(observed), 3, 0, monthly_outputs, iprint="month")
    assert e.obs_masked.count() == 22
    assert e.nash() == pytest.approx(1.0)


def test_fluxes(monthly_outputs):
    f = ReadOut.fluxes("SURQ", [1, 2], 0, monthly_outputs, iprint="month")
    j = fx.SUB_NAMES.index("SURQ")
    expected = (fx.out_value(j, 1, 2002, 1) * 10.0 + fx.out_value(j, 2, 2002, 1) * 15.0) * 1000.0 / 24 / 60 / 60
    assert f.result() == pytest.approx(expected, rel=1e-3)


@pytest.mark.parametrize("mon,iprint,keep", [
    ("    1", "month", True), ("   12", "month", True), (" 2001", "month", False), ("  3.0", "month", False),
    ("  366", "day", True), (" 2001", "day", False), ("  3.0", "day", False),
    (" 2001", "year", True), ("  3.0", "year", False),
])
def test_keep_row(mon, iprint, keep):
    assert ReadOut.keepRow(mon, iprint) is keep
