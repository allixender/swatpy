import os
import shutil
import sys

import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(TESTS_DIR, "data")
REPO_DIR = os.path.dirname(TESTS_DIR)

sys.path.insert(0, DATA_DIR)


@pytest.fixture
def mini_model(tmp_path):
    """A fresh copy of the synthetic mini SWAT2012 TxtInOut (see tests/data/make_fixtures.py)."""
    target = tmp_path / "TxtInOut"
    shutil.copytree(os.path.join(DATA_DIR, "TxtInOut"), target)
    return str(target)


@pytest.fixture
def monthly_outputs(tmp_path):
    target = tmp_path / "output_monthly"
    shutil.copytree(os.path.join(DATA_DIR, "output_monthly"), target)
    return str(target)


@pytest.fixture
def daily_outputs(tmp_path):
    target = tmp_path / "output_daily"
    shutil.copytree(os.path.join(DATA_DIR, "output_daily"), target)
    return str(target)
