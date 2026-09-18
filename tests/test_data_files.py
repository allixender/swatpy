"""Consistency of the calibration inputs in the repository data/ folder."""

import glob
import os
import sys
from datetime import date

import numpy as np
import pytest

from swatpy import FileEdit, SwatModel, parseParameterName

from conftest import REPO_DIR

DATA = os.path.join(REPO_DIR, "data")
SCRIPTS = os.path.join(DATA, "scripts")

# data/ is part of the git repository, not of the sdist
pytestmark = pytest.mark.skipif(not os.path.isdir(DATA), reason="repository data/ folder not available")

# parameter files in the spotpy naming convention, read like data/scripts/run_for.py does
PARAM_FILES = sorted(p for p in glob.glob(os.path.join(DATA, "params", "*.txt"))
                     if not p.endswith("pori3_par_inf.txt")       # SWAT-CUP format, see below
                     and not p.endswith("input_wwr_hp.txt"))      # comma separated, other tool

MANIPULATOR_CLASSES = {
    "bsn": FileEdit.bsnManipulator, "gw": FileEdit.gwManipulator, "mgt": FileEdit.mgtManipulator,
    "sub": FileEdit.subManipulator, "hru": FileEdit.hruManipulator, "rte": FileEdit.rteManipulator,
    "sol": FileEdit.solManipulator,
}


def load_param_file(path):
    dtype = [("f0", "|U30"), ("f1", "<f8"), ("f2", "<f8")]
    return np.atleast_1d(np.genfromtxt(path, dtype=dtype, encoding="utf-8"))


def test_param_files_found():
    names = [os.path.basename(p) for p in PARAM_FILES]
    assert "pori3_par_inf_spotpy.txt" in names
    assert "par_inf2.txt" in names


@pytest.mark.parametrize("path", PARAM_FILES, ids=os.path.basename)
def test_param_file_names_and_ranges(path):
    params = load_param_file(path)
    assert len(params) > 0
    seen = set()
    for name, low, high in params:
        how, param, ext, qualifiers = parseParameterName(name)
        assert ext in MANIPULATOR_CLASSES, name
        assert param in MANIPULATOR_CLASSES[ext].parInfo, name
        assert low <= high, name
        # NB: qualifiers (e.g. landuse in v__CANMX__hru______FRSD) are not evaluated by swatpy,
        # such parameters are applied to all files of the type, the last one given wins
        assert (param, ext, tuple(qualifiers)) not in seen, f"{name} given twice"
        seen.add((param, ext, tuple(qualifiers)))


@pytest.mark.parametrize("path", PARAM_FILES, ids=os.path.basename)
@pytest.mark.parametrize("bound", ["f1", "f2"])
def test_param_file_applies_to_model(mini_model, path, bound):
    params = load_param_file(path)
    model = SwatModel.initFromTxtInOut(mini_model, copy=False, force=True)
    before = {}
    for name in params["f0"]:
        how, param, ext, _ = parseParameterName(name)
        before[name] = []
        for m in model.getFileManipulators()[ext]:
            m.ensureParValue(param)
            before[name].append(list(m.parValue[param]))

    for row in params:
        model.setParameter(row["f0"], row[bound])

    # all parameters are applied, for repeated ones (qualifiers are not evaluated) the last one
    last = {parseParameterName(row["f0"])[1:3]: row for row in params}

    after = model.reloadFileManipulators()
    for row in last.values():
        how, param, ext, _ = parseParameterName(row["f0"])
        dig = MANIPULATOR_CLASSES[ext].parInfo[param][3]
        value = row[bound]
        for orig, m in zip(before[row["f0"]], after[ext]):
            m.ensureParValue(param)
            expected = [{"s": value, "+": v + value, "*": v * (1 + value)}[how] for v in orig]
            assert m.parValue[param] == pytest.approx(expected, abs=10 ** -dig), (row["f0"], m.filename)


def test_swatcup_conversion_reproduces_spotpy_file(tmp_path):
    sys.path.insert(0, SCRIPTS)
    try:
        import convert_from_swatcup
    finally:
        sys.path.remove(SCRIPTS)
    out = tmp_path / "converted.txt"
    convert_from_swatcup.parse(os.path.join(DATA, "params", "pori3_par_inf.txt"), str(out))
    converted = load_param_file(str(out))
    committed = load_param_file(os.path.join(DATA, "params", "pori3_par_inf_spotpy.txt"))
    assert list(converted["f0"]) == list(committed["f0"])
    assert converted["f1"] == pytest.approx(committed["f1"])
    assert converted["f2"] == pytest.approx(committed["f2"])

    # upper case SWAT-CUP prefixes keep their meaning
    swatcup = tmp_path / "par_inf.txt"
    swatcup.write_text("V__GW_DELAY.gw 0 60\nA__GWQMN.gw -10 10\nR__CN2.mgt -0.1 0.1\n")
    convert_from_swatcup.parse(str(swatcup), str(out))
    assert list(load_param_file(str(out))["f0"]) == ["v__GW_DELAY__gw", "a__GWQMN__gw", "r__CN2__mgt"]


def test_observed_monthly_flow():
    path = os.path.join(DATA, "observed", "pori_flow_monthly_2003-2010.txt")
    with open(path) as f:
        rows = [line.strip().split(";") for line in f if line.strip()]
    assert all(len(r) == 3 for r in rows)
    # running index and consecutive months, starting January 2003
    month = date(2003, 1, 1)
    for i, (index, label, value) in enumerate(rows):
        assert int(index) == i + 1
        assert label == "FLOW_OUT_%d_%d" % (month.month, month.year)
        value = float(value)
        assert value >= 0 or value == -9999
        month = date(month.year + month.month // 12, month.month % 12 + 1, 1)


def test_observed_daily_discharge():
    values = np.loadtxt(os.path.join(DATA, "observed", "discharge2.txt"))
    assert values.ndim == 1
    assert len(values) == 1461  # 4 years of daily values, one leap year
    assert np.all((values >= 0) | (values == -9999))
