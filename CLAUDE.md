# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`swatpy` (PyPI: `swatpy`) wraps SWAT2012 (Soil and Water Assessment Tool) models: run the SWAT executable, edit parameters in the fixed-width `TxtInOut` input files, read `output.rch/.sub/.hru`, calibrate with SPOTPY. The package is only `swatpy/`; `data/scripts/` and `notebooks/` are research drivers built on it.

## Commands

```sh
pip install -e ".[dev]"                       # test, build, twine, ruff; [calibration] adds spotpy/scipy/pandas; [docs] adds mkdocs
mkdocs serve                                  # docs/ (MkDocs Material + mkdocstrings), deploys to GitHub Pages via docs.yml
pytest -m "not swat"                          # unit tests, synthetic fixtures, all platforms
pytest tests/test_readout.py -k monthly       # single test / subset
SWATPY_TEST_DOWNLOAD=1 pytest -m swat -rs     # real SWAT2012 rev637 demo project (+ model runs on linux x86_64)
ruff check .                                  # only E9/F63/F7/F82 (syntax, undefined names), legacy code is not style-normalised
python -m build && twine check --strict dist/*
python tests/data/make_fixtures.py            # regenerate synthetic fixtures after changing parInfo/outInfo
```

Version lives in `swatpy/__init__.py` (`__version__`, read dynamically by `pyproject.toml`). Releases: GitHub release `v<version>` → `.github/workflows/publish.yml` → PyPI via trusted publishing (manual dispatch → TestPyPI); the workflow fails if tag and `__version__` differ. Update `CITATION.cff` too.

## Architecture

**`SimManage.SwatModel`**: one model = one working dir (copied or in-place `TxtInOut`) + `.swatmodel.json`. Factories are staticmethods: `initFromTxtInOut(txtInOut, copy=..., target_dir=..., force=...)` (`copy` must be explicit; in-place needs `force=True`), `loadModelFromDirectory(dir)`. Encoding guessed from `file.cio` via chardet (ascii → latin-1). `run()` launches the exe with `cwd=working_dir`, returns the return code (None if it could not start). `getFileManipulators()` caches a dict keyed `fileCio/bsn/gw/sol/hru/rte/sub/mgt` → one manipulator per file; the default parameter lists there are only preloaded, any `parInfo` parameter is read lazily on first change (`ensureParValue`). Urban (`URBN`) soils are skipped. `setParameter("r__CN2__mgt", value)` applies a calibration parameter to all files of that type.

**`FileEdit`** (legacy code, Christoph Hecht 2008): one `InputFileManipulator` subclass per file type, `parInfo` = `name -> (row, col1, col2, digits)`. Read slice is `line[col1:col2]`, write replaces `line[col1-1:col2]` with a `%{col2-col1+1}.{digits}f` field; line endings are preserved (files opened with `newline=""`, ArcSWAT writes CRLF). `setChangePar(name, value, how)` with `how` `s` set / `+` add / `*` relative (`v + v*x`), `finishChangePar()` writes. Changes are computed from values read at construction (`parValue` never updates), but `textNew` is kept after writing, so several parameters of one file can be finished one after another; `resetFile()` restores the original. `solManipulator` handles per-layer lists (12-char columns from col 28). Header attributes (`landuse`, `subbasin`) come from `headerValue()` regexes on line 1. `parInfo` rows were verified against real rev637 files (`tests/test_swat_demo.py::test_parinfo_rows_match_file_labels`, aliases PRF_BSN→PRF, CH_EQ→CH_EQN).

**`ReadOut`**: `rch/sub/hruOutputManipulator` use `outInfo` for the fixed key columns (area id, MON, area size, `valueStart`, `valueWidth`) and derive value columns from the header line (`readColumns`, label → name via `variables` longest-prefix match), because `file.cio` can restrict printed variables. Some fields are one char wider than their label (`widen`: sub CHOLA, hru BACTP/BACTLP) and shift the following columns. `keepRow` filters by MON: monthly keeps 1..12 (drops yearly rows `MON=<year>`), daily 1..366, and the closing average row (`MON` with a dot) is always dropped. Results in `outValues[var][area]`. `efficiency` (NSE `nash`, `agr`) masks `-9999` observations.

**Calibration** (`data/scripts/main.py` demos, `data/scripts/run_for.py` production, SLURM `*.sh` there): `swat_callib_setup` is a SPOTPY setup; each `simulation()` copies the model to a `swat_<uuid>` temp dir, applies parameters, runs SWAT, reads reach 1 monthly `FLOW_OUT`, deletes the dir. The class is duplicated in both scripts; keep in sync. `run_for.py` expects cwd with `<model>/<path>`, `params/`, `observed/` and hardcodes `~/bin/swat_rel670_static`.

**Parameter names** (`data/params/*.txt`, whitespace `name low high`): `<v|r|a>__<PARAM>__<ext>[__hydgrp__soltext__landuse__subbsn__slope]`, parsed by `parseParameterName`. Qualifiers are parsed but not applied (last duplicate wins). SWAT-CUP files (`r__CN2.mgt`) are converted by `data/scripts/convert_from_swatcup.py`; `pori3_par_inf.txt` → `pori3_par_inf_spotpy.txt` is a regression test.

## Tests

- `tests/data/TxtInOut`, `output_monthly`, `output_daily`: synthetic, MIT, generated by `make_fixtures.py` (values encode row/column/time so misalignment shows); `.gitattributes` keeps them byte-exact (`-text`).
- `tests/test_data_files.py` checks the repo `data/` folder (skips in the sdist).
- `tests/test_swat_demo.py` (`swat` marker, `swat_run` for model runs): SWATdata project + exe, GPL-3, downloaded/checksummed, cached in `~/.cache/swatpy-tests`, never vendored. The exe is linux x86_64; under qemu (e.g. podman on Apple Silicon) it segfaults when the project sits on the container overlay fs, use `--basetemp` on a mounted volume.
