"""Reading and manipulating SWAT input files (FileEdit) on the synthetic mini model."""

import os

import pytest

from swatpy import FileEdit

import make_fixtures as fx

# (extension, manipulator class, fixture file, number of lines in that file)
FILES = [
    ("bsn", FileEdit.bsnManipulator, "basins.bsn"),
    ("gw", FileEdit.gwManipulator, "000010001.gw"),
    ("mgt", FileEdit.mgtManipulator, "000010001.mgt"),
    ("sub", FileEdit.subManipulator, "000010000.sub"),
    ("hru", FileEdit.hruManipulator, "000010001.hru"),
    ("rte", FileEdit.rteManipulator, "000010000.rte"),
    ("cio", FileEdit.fileCioManipulator, "file.cio"),
]


def read_text(path):
    with open(path, encoding="latin-1") as f:
        return f.readlines()


@pytest.mark.parametrize("ext,cls,filename", FILES)
def test_all_parameters_read_from_their_row(mini_model, ext, cls, filename):
    m = cls(filename, list(cls.parInfo), mini_model)
    file_id = filename.split(".")[0]
    for name in cls.parInfo:
        assert m.parValue[name] == [pytest.approx(fx.expected_input_value(ext, name, file_id))], name


@pytest.mark.parametrize("ext,cls,filename", FILES)
@pytest.mark.parametrize("how,change", [("s", 7.5), ("+", 1.5), ("*", 0.2)])
def test_change_writes_value_and_only_that_line(mini_model, ext, cls, filename, how, change):
    file_id = filename.split(".")[0]
    names = [n for n, (row, c1, c2, dig) in cls.parInfo.items() if dig > 0]
    if not names:
        pytest.skip("only integer parameters")
    path = os.path.join(mini_model, filename)
    before = read_text(path)
    for name in names:
        row, col1, col2, dig = cls.parInfo[name]
        orig = fx.expected_input_value(ext, name, file_id)
        expected = {"s": change, "+": orig + change, "*": orig * (1 + change)}[how]

        m = cls(filename, [name], mini_model)
        m.setChangePar(name, change, how)
        m.finishChangePar()

        after = read_text(path)
        assert len(after) == len(before)
        changed = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
        assert changed in ([], [row - 1]), name
        # field width and the "|" label separator stay in place
        assert len(after[row - 1]) == len(before[row - 1])
        assert after[row - 1][col2:] == before[row - 1][col2:]

        reread = cls(filename, [name], mini_model)
        assert reread.parValue[name][0] == pytest.approx(expected, abs=10 ** -dig), name

        # restore for the next parameter
        with open(path, "w", encoding="latin-1", newline="") as f:
            f.writelines(before)


@pytest.mark.parametrize("ext,cls,filename", FILES)
def test_noop_change_keeps_file_identical(mini_model, ext, cls, filename):
    path = os.path.join(mini_model, filename)
    with open(path, "rb") as f:
        before = f.read()
    m = cls(filename, list(cls.parInfo), mini_model)
    for name in cls.parInfo:
        m.setChangePar(name, 0, "+")
    m.finishChangePar()
    with open(path, "rb") as f:
        assert f.read() == before


def test_crlf_line_endings_are_kept(mini_model):
    # ArcSWAT projects come with CRLF line endings
    path = os.path.join(mini_model, "000010001.gw")
    with open(path, "rb") as f:
        crlf = f.read().replace(b"\n", b"\r\n")
    with open(path, "wb") as f:
        f.write(crlf)
    m = FileEdit.gwManipulator("000010001.gw", ["GW_DELAY"], mini_model)
    m.setChangePar("GW_DELAY", 0, "+")
    m.finishChangePar()
    with open(path, "rb") as f:
        assert f.read() == crlf
    m.setChangePar("GW_DELAY", 12.0, "s")
    m.finishChangePar()
    with open(path, "rb") as f:
        text = f.read()
    assert text.count(b"\r\n") == crlf.count(b"\r\n") and b"\r\r" not in text
    assert FileEdit.gwManipulator("000010001.gw", ["GW_DELAY"], mini_model).parValue["GW_DELAY"] == [12.0]


def test_changes_are_relative_to_original_file_values(mini_model):
    # parValue keeps the values read at construction, repeated edits do not accumulate
    m = FileEdit.gwManipulator("000010001.gw", ["GW_DELAY"], mini_model)
    orig = m.parValue["GW_DELAY"][0]
    for _ in range(3):
        m.setChangePar("GW_DELAY", 1.0, "+")
        m.finishChangePar()
    assert FileEdit.gwManipulator("000010001.gw", ["GW_DELAY"], mini_model).parValue["GW_DELAY"][0] == pytest.approx(orig + 1)


def test_changes_of_several_parameters_are_all_kept(mini_model):
    # the calibration scripts call finishChangePar after every single parameter
    path = os.path.join(mini_model, "000010001.gw")
    with open(path, "rb") as f:
        original = f.read()
    names = ["GW_DELAY", "ALPHA_BF", "GWQMN"]
    m = FileEdit.gwManipulator("000010001.gw", names, mini_model)
    for name, value in zip(names, [20.0, 0.05, 500.0]):
        m.setChangePar(name, value, "s")
        m.finishChangePar()
    reread = FileEdit.gwManipulator("000010001.gw", names, mini_model)
    assert [reread.parValue[n][0] for n in names] == [20.0, 0.05, 500.0]

    m.resetFile()
    with open(path, "rb") as f:
        assert f.read() == original


def test_parameters_not_in_parlist_are_read_on_first_use(mini_model):
    m = FileEdit.rteManipulator("000010000.rte", ["CH_N2"], mini_model)
    assert m.parValue["ALPHA_BNK"] is None
    m.setChangePar("ALPHA_BNK", 0.5, "*")
    m.finishChangePar()
    orig = fx.expected_input_value("rte", "ALPHA_BNK")
    assert FileEdit.rteManipulator("000010000.rte", ["ALPHA_BNK"], mini_model).parValue["ALPHA_BNK"][0] == pytest.approx(orig * 1.5)


def test_invalid_change_raises(mini_model):
    m = FileEdit.gwManipulator("000010001.gw", ["GW_DELAY"], mini_model)
    with pytest.raises(ValueError):
        m.setChangePar("GW_DELAY", 1.0, "x")
    with pytest.raises(KeyError):
        m.setChangePar("NOT_A_PARAMETER", 1.0, "s")


def test_parlist_argument_is_not_modified(mini_model):
    par_list = ["ESCO"]
    FileEdit.hruManipulator("000010001.hru", par_list, mini_model)
    sol_list = ["SOL_K"]
    FileEdit.solManipulator("000010001.sol", sol_list, mini_model)
    assert par_list == ["ESCO"]
    assert sol_list == ["SOL_K"]


@pytest.mark.parametrize("file_id", list(fx.HRUS))
def test_header_attributes(mini_model, file_id):
    sub, hru, luse, soil, fr = fx.HRUS[file_id]
    for cls, ext in [(FileEdit.hruManipulator, "hru"), (FileEdit.gwManipulator, "gw"),
                     (FileEdit.mgtManipulator, "mgt")]:
        m = cls(file_id + "." + ext, [], mini_model)
        assert m.landuse == luse
        assert m.subbasin == str(sub)
    assert FileEdit.solManipulator(file_id + ".sol", [], mini_model).landuse == luse
    h = FileEdit.hruManipulator(file_id + ".hru", [], mini_model)
    assert h.hru_abs == pytest.approx(fx.SUBBASINS[sub] * fr)


@pytest.mark.parametrize("sub", list(fx.SUBBASINS))
def test_rte_subbasin_from_header(mini_model, sub):
    assert FileEdit.rteManipulator("%05d0000.rte" % sub, [], mini_model).subbasin == str(sub)


# ---------------------------------------------------------------------------------------
# soil files: several layers per parameter

SOL_PARS = list(FileEdit.solManipulator.parInfo)


@pytest.mark.parametrize("file_id", list(fx.HRUS))
def test_sol_values(mini_model, file_id):
    soil = fx.SOILS[fx.HRUS[file_id][3]]
    m = FileEdit.solManipulator(file_id + ".sol", SOL_PARS, mini_model)
    for name in SOL_PARS:
        expected = soil[name] if isinstance(soil[name], list) else [soil[name]]
        assert m.parValue[name] == pytest.approx(expected), name
    # SOL_ZMX is read completely, not only the last digits
    assert m.parValue["SOL_ZMX"][0] == soil["SOL_ZMX"]
    # depth weighted profile mean
    z = soil["SOL_Z"]
    thickness = [z[0]] + [z[i] - z[i - 1] for i in range(1, len(z))]
    mean_k = sum(k * t for k, t in zip(soil["SOL_K"], thickness)) / z[-1]
    assert m.parValueMean["SOL_K"] == pytest.approx(mean_k)


@pytest.mark.parametrize("how,change", [("s", 12.5), ("+", 1.0), ("*", -0.1)])
def test_sol_change_all_layers(mini_model, how, change):
    soil = fx.SOILS["SOILA"]
    m = FileEdit.solManipulator("000010001.sol", ["SOL_K"], mini_model)
    m.setChangePar("SOL_K", change, how)
    m.finishChangePar()
    expected = [{"s": change, "+": k + change, "*": k * (1 + change)}[how] for k in soil["SOL_K"]]
    assert FileEdit.solManipulator("000010001.sol", ["SOL_K"], mini_model).parValue["SOL_K"] == pytest.approx(expected, abs=1e-4)


def test_sol_change_single_layer(mini_model):
    soil = fx.SOILS["SOILA"]
    m = FileEdit.solManipulator("000010001.sol", ["SOL_AWC"], mini_model)
    m.setChangeParLay("SOL_AWC", 0.33, "s", 1)
    m.finishChangePar()
    expected = list(soil["SOL_AWC"])
    expected[1] = 0.33
    assert FileEdit.solManipulator("000010001.sol", ["SOL_AWC"], mini_model).parValue["SOL_AWC"] == pytest.approx(expected)


@pytest.mark.parametrize("name", ["SOL_ZMX", "SOL_CRK", "ANION_EXCL"])
def test_sol_single_value_parameters_roundtrip(mini_model, name):
    m = FileEdit.solManipulator("000010001.sol", [name], mini_model)
    orig = m.parValue[name][0]
    m.setChangePar(name, 0.1, "*")
    m.finishChangePar()
    assert FileEdit.solManipulator("000010001.sol", [name], mini_model).parValue[name][0] == pytest.approx(orig * 1.1, abs=1e-2)


def test_sol_noop_change_keeps_values(mini_model):
    # layer values are written with parInfo digits (4), ArcSWAT writes 2, so compare values
    before = FileEdit.solManipulator("000010001.sol", SOL_PARS, mini_model).parValue
    m = FileEdit.solManipulator("000010001.sol", SOL_PARS, mini_model)
    for name in SOL_PARS:
        m.setChangePar(name, 0, "+")
    m.finishChangePar()
    after = FileEdit.solManipulator("000010001.sol", SOL_PARS, mini_model).parValue
    for name in SOL_PARS:
        assert after[name] == pytest.approx(before[name]), name


def test_sol_texture_correction_and_check(mini_model):
    soil = fx.SOILS["SOILA"]
    m = FileEdit.solManipulator("000010001.sol", ["SAND"], mini_model)
    m.setChangePar("SAND", 0.5, "*")  # texture no longer sums up to 100 %
    m.finishChangePar()
    FileEdit.solManipulationCorrection("000010001.sol", mini_model)
    m = FileEdit.solManipulator("000010001.sol", ["CLAY", "SILT", "SAND"], mini_model)
    assert m.parValue["CLAY"] == pytest.approx(soil["CLAY"])
    for clay, silt, sand in zip(m.parValue["CLAY"], m.parValue["SILT"], m.parValue["SAND"]):
        assert clay + silt + sand == pytest.approx(100.0, abs=0.01)
    assert FileEdit.solManipulationCheck("000010001.sol", mini_model).ok
