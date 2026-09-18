# Usage

## Creating and loading a model

A model is a working copy of an ArcSWAT `TxtInOut` folder plus a small metadata file
(`.swatmodel.json`). Use one of the two factory methods:

```python
from swatpy import SwatModel

# copy TxtInOut to a new working directory (target_dir), or to ./swat_<uuid> when omitted
model = SwatModel.initFromTxtInOut("path/to/TxtInOut", copy=True, target_dir="work")

# in-place work in the original folder requires an explicit confirmation
model = SwatModel.initFromTxtInOut("path/to/TxtInOut", copy=False, force=True)

# later: reload the metadata from an existing working directory
model = SwatModel.loadModelFromDirectory("work")
```

`initFromTxtInOut(..., copy=...)` must be passed explicitly — `copy=None` raises a
`ValueError` — so you always state whether you work on a copy or in place. The model text
encoding is guessed from `file.cio` via `chardet` (`ascii` falls back to `latin-1`).

Read the simulation layout into the metadata object:

```python
model.enrichModelMeta()
# model.n_sub_basins, model.n_hru, model.n_years_simulated,
# model.beginning_year_simulation, model.readout_years, model.readout_days, ...
```

## Setting parameters

Calibration parameters use SWAT-CUP style names `<v|r|a>__<PARAM>__<ext>`, where the
prefix selects the change mode:

| Prefix | Mode | Effect |
| --- | --- | --- |
| `v` | replace | set the parameter to the value |
| `r` | relative | `value * (1 + x)` |
| `a` | add | `value + x` |

```python
model.setParameter("r__CN2__mgt", -0.1)        # CN2 * (1 - 0.1) in all .mgt files
model.setParameter("v__GW_DELAY__gw", 30.0)    # replace in all .gw files
model.setParameter("a__SOL_AWC__sol", 0.02)    # add to all soil layers
```

`setParameter` applies the change to every file of that type (see
[Parameters](parameters.md) for the available names and file types). Changes are computed
from the values read when the file manipulators were first created, so repeated calibration
runs do not accumulate, and several parameters of the same file are all kept.

The file manipulators are also available directly for finer control:

```python
manipulators = model.getFileManipulators()
for m in manipulators["mgt"]:
    m.setChangePar("CN2", -0.1, "*")
    m.finishChangePar()          # writes the file

for m in manipulators["mgt"]:
    m.resetFile()                # restore the original content
```

## Running SWAT

```python
model.swat_exec = "/path/to/swat2012"
returncode = model.run(silent=True, capture_logs=True)
# returncode is 0 on success, None if the executable could not start
# model.last_run_succesful, model.last_run_logs
```

SWAT reads `file.cio` from the current directory, so the process runs with
`cwd=model.working_dir`.

## Reading results

```python
from swatpy import rchOutputManipulator, subOutputManipulator, hruOutputManipulator

reach = rchOutputManipulator(
    ["FLOW_OUT"], [1],
    "skip", True, 0,             # no file output: method="skip", onlyStatistics, daysSkip
    model.working_dir,
    iprint="month",              # or "day"; must match file.cio IPRINT
)
flow = reach.outValues["FLOW_OUT"][1]   # dict var -> {area -> list of values}
```

The constructor signature is shared by the three readers:

```
<rch|sub|hru>OutputManipulator(outList, areasList, method, onlyStatistics, daysSkip,
                               working_dir, iprint='day', stats_dir=None, encoding='latin-1')
```

- `outList` — output variable names (e.g. `FLOW_OUT`), read from the header line;
- `areasList` — reach / subbasin / HRU ids;
- `method` — `"skip"` (no file output), `"sum"`, `"indi"` or `"sum & indi"`;
- `onlyStatistics` — when writing files, write only mean/median/variance;
- `daysSkip` — warm-up days ignored for the statistics.

Column positions are derived from the header line, so a reduced selection of printed
variables in `file.cio` is read correctly. Yearly summary rows in monthly output and the
closing average-annual row are skipped.

For a complete walk-through including calibration with SPOTPY see the `data/scripts`
drivers in the repository.
