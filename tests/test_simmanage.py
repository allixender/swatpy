"""SwatModel working directory handling, metadata and model runs on the synthetic mini model."""

import json
import os
import sys

import pytest

from swatpy import SwatModel

import make_fixtures as fx


def test_init_requires_explicit_copy_decision(mini_model):
    with pytest.raises(ValueError):
        SwatModel.initFromTxtInOut(mini_model)
    with pytest.raises(ValueError):
        SwatModel.initFromTxtInOut(mini_model, copy=False)


def test_init_copy_and_load(mini_model, tmp_path):
    target = tmp_path / "work"
    model = SwatModel.initFromTxtInOut(mini_model, copy=True, target_dir=str(target))
    assert os.path.samefile(model.working_dir, target)
    assert sorted(os.listdir(target)) == sorted(os.listdir(mini_model) + [".swatmodel.json"])
    with open(target / ".swatmodel.json") as f:
        meta = json.load(f)
    assert meta["swat_version"] == "2012"
    assert meta["model_text_encoding"] == "latin-1"  # ascii is redirected to latin-1

    loaded = SwatModel.loadModelFromDirectory(str(target))
    assert loaded.working_dir == model.working_dir

    # the target exists and is not empty now
    with pytest.raises(ValueError):
        SwatModel.initFromTxtInOut(mini_model, copy=True, target_dir=str(target))


def test_init_in_place(mini_model):
    model = SwatModel.initFromTxtInOut(mini_model, copy=False, force=True)
    assert os.path.exists(os.path.join(mini_model, ".swatmodel.json"))
    assert os.path.samefile(model.working_dir, mini_model)


def test_load_missing_directory_raises(tmp_path):
    with pytest.raises(ValueError):
        SwatModel.loadModelFromDirectory(str(tmp_path / "does_not_exist"))
    with pytest.raises(ValueError):
        SwatModel.loadModelFromDirectory(str(tmp_path))  # no .swatmodel.json


def test_file_manipulators(mini_model):
    model = SwatModel.initFromTxtInOut(mini_model, copy=False, force=True)
    manipulators = model.getFileManipulators()
    counts = {key: len(value) for key, value in manipulators.items()}
    # the urban HRU 000010002 has no soil manipulator
    assert counts == {"fileCio": 1, "bsn": 1, "gw": 3, "sol": 2, "hru": 3, "rte": 2, "sub": 2, "mgt": 3}
    assert model.getFileManipulators() is manipulators
    assert model.reloadFileManipulators() is not manipulators


def test_enrich_model_meta(mini_model):
    model = SwatModel.initFromTxtInOut(mini_model, copy=False, force=True)
    meta = model.enrichModelMeta(verbose=False)
    assert meta["n_sub_basins"] == 2
    assert meta["n_hru"] == 3
    assert meta["beginning_year_simulation"] == fx.IYR
    assert meta["n_years_simulated"] == fx.NBYR
    assert meta["n_years_skip"] == fx.NYSKIP
    assert meta["n_days_skip"] == 365          # 2001
    assert meta["readout_years"] == 2          # 2002, 2003
    assert meta["readout_days"] == 730
    with open(os.path.join(mini_model, ".swatmodel.json")) as f:
        assert json.load(f)["readout_days"] == 730


def test_manipulate_through_model(mini_model):
    model = SwatModel.initFromTxtInOut(mini_model, copy=False, force=True)
    for m in model.getFileManipulators()["mgt"]:
        m.setChangePar("CN2", 0.1, "*")
        m.finishChangePar()
    cn2 = fx.expected_input_value("mgt", "CN2")
    for m in model.reloadFileManipulators()["mgt"]:
        assert m.parValue["CN2"][0] == pytest.approx(cn2 * 1.1, abs=1e-3)


posix_only = pytest.mark.skipif(sys.platform == "win32", reason="fake SWAT executable is a shell script")


def fake_swat(working_dir, script):
    path = os.path.join(working_dir, "swat_fake")
    with open(path, "w", newline="\n") as f:
        f.write("#!/bin/sh\n" + script)
    os.chmod(path, 0o755)
    return "swat_fake"


@posix_only
def test_run_success_in_working_dir(mini_model):
    model = SwatModel.initFromTxtInOut(mini_model, copy=False, force=True)
    model.swat_exec = fake_swat(mini_model, "test -f file.cio || exit 3\necho ' Execution successfully completed '\n")
    assert model.run(capture_logs=True, silent=True) == 0
    assert model.last_run_succesful
    assert "Execution successfully completed" in model.last_run_logs


@posix_only
def test_run_failure(mini_model):
    model = SwatModel.initFromTxtInOut(mini_model, copy=False, force=True)
    model.swat_exec = fake_swat(mini_model, "echo broken\nexit 2\n")
    assert model.run(capture_logs=True, silent=True) == 2
    assert not model.last_run_succesful
    assert model.last_run_logs == "broken"


def test_run_missing_executable(mini_model):
    model = SwatModel.initFromTxtInOut(mini_model, copy=False, force=True)
    model.swat_exec = "no_such_swat_executable"
    assert model.run(silent=True) is None
    assert not model.last_run_succesful
    assert model.last_run_logs
