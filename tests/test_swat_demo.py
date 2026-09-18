"""Consistency checks on a real SWAT2012 project and model runs.

Uses the SWAT2012 rev 637 demo project (Little River head watershed) and the rev 637 linux
executable from https://github.com/chrisschuerz/SWATdata (GPL-3, downloaded, not vendored).

    SWATPY_TEST_DOWNLOAD=1   allow the download (otherwise the tests are skipped unless cached)
    SWATPY_TEST_CACHE        cache directory, default ~/.cache/swatpy-tests
    SWATPY_SWAT_EXE          SWAT2012 executable to use instead of the downloaded one
"""

import hashlib
import os
import platform
import re
import stat
import sys
import urllib.request
import zipfile
from calendar import monthrange

import numpy as np
import pytest

from swatpy import FileEdit, ReadOut, SwatModel

pytestmark = pytest.mark.swat

SWATDATA = "https://github.com/chrisschuerz/SWATdata/raw/2cd16e3f2453063362e32350041d57c1646e780f/inst/extdata/"
PROJECT_ZIP = ("2012_rev637_project.zip", "f65742321b0c07466110afe8950efe40f3504b7d9af3220b851e7620e42be77b")
EXE_ZIP = ("2012_rev637_unix.zip", "86f16d656228f2e4851f52072370af828fdbb0551b66579d1842f2d61f88542b")

# parInfo names that differ from the labels in the files
LABEL_ALIASES = {"PRF_BSN": "PRF", "CH_EQ": "CH_EQN"}


def cache_dir():
    return os.environ.get("SWATPY_TEST_CACHE", os.path.join(os.path.expanduser("~"), ".cache", "swatpy-tests"))


def fetch(name, sha256):
    path = os.path.join(cache_dir(), name)
    if not os.path.exists(path):
        if os.environ.get("SWATPY_TEST_DOWNLOAD") != "1":
            pytest.skip("SWATdata not cached, set SWATPY_TEST_DOWNLOAD=1 to download")
        os.makedirs(cache_dir(), exist_ok=True)
        urllib.request.urlretrieve(SWATDATA + name, path + ".part")
        os.replace(path + ".part", path)
    with open(path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    assert digest == sha256, f"unexpected checksum of {path}"
    return path


def match_file_cio_case(project):
    # file.cio references "tmp1.tmp" but the project ships "Tmp1.Tmp", which only
    # works on case-insensitive file systems
    files = {name.lower(): name for name in os.listdir(project)}
    with open(os.path.join(project, "file.cio"), encoding="latin-1") as f:
        referenced = [line.split()[0] for line in f if line.strip() and "." in line.split()[0]]
    for name in referenced:
        actual = files.get(name.lower())
        if actual is not None and actual != name:
            os.rename(os.path.join(project, actual), os.path.join(project, name))


@pytest.fixture(scope="session")
def demo_project(tmp_path_factory):
    target = tmp_path_factory.mktemp("swatdata")
    with zipfile.ZipFile(fetch(*PROJECT_ZIP)) as z:
        z.extractall(target)
    project = str(target / "swat2012_rev637_demo")
    match_file_cio_case(project)
    return project


@pytest.fixture(scope="session")
def swat_exe(tmp_path_factory):
    if os.environ.get("SWATPY_SWAT_EXE"):
        return os.path.abspath(os.environ["SWATPY_SWAT_EXE"])
    if not (sys.platform.startswith("linux") and platform.machine() in ("x86_64", "AMD64")):
        pytest.skip("the SWAT2012 rev 637 executable from SWATdata runs on linux x86_64 only")
    target = tmp_path_factory.mktemp("swatexe")
    with zipfile.ZipFile(fetch(*EXE_ZIP)) as z:
        z.extractall(target)
    exe = target / "swat2012_rev637"
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    return str(exe)


@pytest.fixture
def demo_model(demo_project, tmp_path):
    return SwatModel.initFromTxtInOut(demo_project, copy=True, target_dir=str(tmp_path / "TxtInOut"))


# ---------------------------------------------------------------------------------------
# input files

FILES = [
    (FileEdit.bsnManipulator, "basins.bsn"),
    (FileEdit.gwManipulator, "000010001.gw"),
    (FileEdit.mgtManipulator, "000010001.mgt"),
    (FileEdit.subManipulator, "000010000.sub"),
    (FileEdit.hruManipulator, "000010001.hru"),
    (FileEdit.rteManipulator, "000010000.rte"),
    (FileEdit.fileCioManipulator, "file.cio"),
]


@pytest.mark.parametrize("cls,filename", FILES, ids=[f for c, f in FILES])
def test_parinfo_rows_match_file_labels(demo_project, cls, filename):
    with open(os.path.join(demo_project, filename), encoding="latin-1") as f:
        lines = f.readlines()
    checked = 0
    for name, (row, col1, col2, dig) in cls.parInfo.items():
        if row > len(lines):
            continue  # newer SWAT revisions have additional parameters at the end of the file
        label = re.search(r"\|\s*([A-Za-z0-9_]+)", lines[row - 1])
        assert label is not None and label.group(1) == LABEL_ALIASES.get(name, name), (name, lines[row - 1])
        # the value sits within the columns described by parInfo
        float(lines[row - 1][col1 - 1:col2])
        checked += 1
    assert checked >= len(cls.parInfo) - 8


def test_header_values(demo_project):
    sol = FileEdit.solManipulator("000010001.sol", ["SOL_ZMX", "SOL_Z", "SOL_K"], demo_project)
    assert sol.parValue["SOL_ZMX"] == [1520.0]
    assert sol.parValue["SOL_Z"] == [360.0, 1070.0, 1520.0]
    assert sol.parValue["SOL_K"] == [100.8, 32.4, 9.72]
    assert sol.landuse == "AGRL"
    rte = FileEdit.rteManipulator("000030000.rte", [], demo_project)
    assert rte.subbasin == "3"
    hru = FileEdit.hruManipulator("000010001.hru", [], demo_project)
    assert (hru.subbasin, hru.landuse) == ("1", "AGRL")
    assert hru.hru_abs == pytest.approx(8.7822 * 0.0211109)


def test_model_metadata_and_manipulators(demo_model):
    files = os.listdir(demo_model.working_dir)
    manipulators = demo_model.getFileManipulators()
    assert len(manipulators["hru"]) == len([f for f in files if f.endswith(".hru") and f.startswith("0")])
    assert len(manipulators["sub"]) == len([f for f in files if f.endswith(".sub") and f.startswith("0")])
    assert len(manipulators["mgt"]) == len(manipulators["gw"]) == len(manipulators["hru"])
    meta = demo_model.enrichModelMeta(verbose=False)
    assert (meta["beginning_year_simulation"], meta["n_years_simulated"], meta["n_years_skip"]) == (2000, 13, 3)
    assert meta["readout_days"] == 3653  # 2003-2012


def test_noop_manipulation_keeps_all_values(demo_model):
    before = {key: [dict(m.parValue) for m in ms] for key, ms in demo_model.getFileManipulators().items()}
    for key, ms in demo_model.getFileManipulators().items():
        for m in ms:
            for name, value in m.parValue.items():
                if value is not None:
                    m.setChangePar(name, 0, "+")
            m.finishChangePar()
    after = {key: [dict(m.parValue) for m in ms] for key, ms in demo_model.reloadFileManipulators().items()}
    for key in before:
        for b, a in zip(before[key], after[key]):
            for name in b:
                if b[name] is not None:
                    assert a[name] == pytest.approx(b[name]), (key, name)


# ---------------------------------------------------------------------------------------
# model runs


def prepare_run(demo_model, swat_exe, iprint, nbyr=5, nyskip=3):
    # 2000-2004, printed 2003 and 2004 (2004 is a leap year, IDAL=366 in the demo file.cio)
    cio = FileEdit.fileCioManipulator("file.cio", [], demo_model.working_dir)
    cio.setChangePar("NBYR", nbyr, "s")
    cio.setChangePar("NYSKIP", nyskip, "s")
    cio.setChangePar("IPRINT", iprint, "s")
    cio.finishChangePar()
    demo_model.swat_exec = swat_exe
    demo_model.reloadFileManipulators()
    return demo_model


def run_ok(model):
    returncode = model.run(capture_logs=True, silent=True)
    assert returncode == 0, model.last_run_logs[-2000:]
    assert model.last_run_succesful
    assert "Execution successfully completed" in model.last_run_logs


def token_values(reader, areas):
    # the reference: whitespace split of the value part of each kept row
    names = list(reader.columns)
    values = {name: {area: [] for area in areas} for name in names}
    for area, row in reader.dataRows():
        if area in areas:
            tokens = row[reader.outInfo["valueStart"]:].split()
            assert len(tokens) == len(names)
            for name, token in zip(names, tokens):
                values[name][area].append(float(token))
    return values


@pytest.fixture(scope="module")
def daily_run(demo_project, swat_exe, tmp_path_factory):
    model = SwatModel.initFromTxtInOut(demo_project, copy=True, target_dir=str(tmp_path_factory.mktemp("daily") / "m"))
    run_ok(prepare_run(model, swat_exe, iprint=1))
    return model


@pytest.fixture(scope="module")
def monthly_run(demo_project, swat_exe, tmp_path_factory):
    model = SwatModel.initFromTxtInOut(demo_project, copy=True, target_dir=str(tmp_path_factory.mktemp("monthly") / "m"))
    run_ok(prepare_run(model, swat_exe, iprint=0))
    return model


@pytest.mark.swat_run
@pytest.mark.parametrize("cls", [ReadOut.rchOutputManipulator, ReadOut.subOutputManipulator])
def test_daily_readout_matches_tokens_and_metadata(daily_run, cls):
    meta = daily_run.enrichModelMeta(verbose=False, update_meta=False)
    assert meta["readout_days"] == 731
    reader = cls([], [1, 2, 3], "skip", True, 0, daily_run.working_dir, iprint="day")
    reader = cls(list(reader.columns), [1, 2, 3], "skip", True, 0, daily_run.working_dir, iprint="day")
    assert len(reader.outValues["PRECIP" if "PRECIP" in reader.columns else "FLOW_OUT"][1]) == meta["readout_days"]
    assert reader.outValues == token_values(reader, [1, 2, 3])


@pytest.mark.swat_run
def test_monthly_readout_matches_daily(daily_run, monthly_run):
    daily = ReadOut.rchOutputManipulator(["FLOW_OUT"], [3], "skip", True, 0, daily_run.working_dir, iprint="day")
    monthly = ReadOut.rchOutputManipulator(["FLOW_OUT"], [3], "skip", True, 0, monthly_run.working_dir, iprint="month")
    flow_daily = np.array(daily.outValues["FLOW_OUT"][3])
    flow_monthly = monthly.outValues["FLOW_OUT"][3]
    assert len(flow_monthly) == 24
    daily_means = []
    start = 0
    for year, month in [(y, m) for y in (2003, 2004) for m in range(1, 13)]:
        days = monthrange(year, month)[1]
        daily_means.append(flow_daily[start:start + days].mean())
        start += days
    # monthly reach output is the mean flow of the month; SWAT rev 637 apparently averages
    # February of the first printed year (2003) over 27 days (ratio 28/27), all other months agree
    ratios = np.array(flow_monthly) / np.array(daily_means)
    assert ratios[1] == pytest.approx(28 / 27, rel=2e-3)
    assert np.delete(ratios, 1) == pytest.approx(1.0, rel=2e-3)

    precip_daily = ReadOut.subOutputManipulator(["PRECIP"], [1], "skip", True, 0, daily_run.working_dir, iprint="day")
    precip_monthly = ReadOut.subOutputManipulator(["PRECIP"], [1], "skip", True, 0, monthly_run.working_dir, iprint="month")
    assert sum(precip_monthly.outValues["PRECIP"][1]) == pytest.approx(sum(precip_daily.outValues["PRECIP"][1]), rel=1e-3)


def sub_totals(model, name):
    reader = ReadOut.subOutputManipulator([name], [1, 2, 3], "skip", True, 0, model.working_dir, iprint="month")
    return sum(sum(v) for v in reader.outValues[name].values())


@pytest.mark.swat_run
def test_noop_parameter_changes_keep_results(demo_project, swat_exe, monthly_run, tmp_path):
    model = prepare_run(SwatModel.initFromTxtInOut(demo_project, copy=True, target_dir=str(tmp_path / "m")), swat_exe, iprint=0)
    for key, ms in model.getFileManipulators().items():
        for m in ms:
            for name, value in m.parValue.items():
                if value is not None and key != "fileCio":
                    m.setChangePar(name, 0, "+")
            m.finishChangePar()
    run_ok(model)
    for name in ("SURQ", "GW_Q", "WYLD"):
        assert sub_totals(model, name) == pytest.approx(sub_totals(monthly_run, name), rel=1e-6)


@pytest.mark.swat_run
def test_parameter_changes_have_expected_effect(demo_project, swat_exe, monthly_run, tmp_path):
    model = prepare_run(SwatModel.initFromTxtInOut(demo_project, copy=True, target_dir=str(tmp_path / "m")), swat_exe, iprint=0)
    # several parameters of the same file types, applied one by one like the calibration scripts do
    model.setParameter("r__CN2__mgt", 0.15)
    model.setParameter("v__GW_DELAY__gw", 200.0)
    model.setParameter("v__ALPHA_BF__gw", 0.01)
    model.setParameter("r__SOL_ZMX__sol", -0.1)  # the field reaches the end of the line
    run_ok(model)
    assert sub_totals(model, "SURQ") > 1.2 * sub_totals(monthly_run, "SURQ")
    assert sub_totals(model, "GW_Q") < sub_totals(monthly_run, "GW_Q")
    gw = FileEdit.gwManipulator("000010001.gw", ["GW_DELAY", "ALPHA_BF"], model.working_dir)
    assert (gw.parValue["GW_DELAY"], gw.parValue["ALPHA_BF"]) == ([200.0], [0.01])
