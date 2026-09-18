# swatpy

A set of Python modules to work with the Soil and Water Assessment Tool
([SWAT2012](https://swat.tamu.edu/)): run model executables, edit parameters in the
fixed-width `TxtInOut` input files, read simulation outputs (`output.rch`, `output.sub`,
`output.hru`) and calibrate models with [SPOTPY](https://pypi.org/project/spotpy/).

<div class="grid cards" markdown>

- :material-rocket-launch: **[Usage](usage.md)** — create a model, change parameters, run SWAT and read results
- :material-tune-variant: **[Parameters](parameters.md)** — the `<v|r|a>__<PARAM>__<ext>` parameter names and file types
- :material-chart-line: **[Output readers](readout.md)** — read `output.rch` / `.sub` / `.hru` and compute efficiency
- :material-code-braces: **[API reference](api.md)** — `SwatModel`, the file manipulators and the output readers

</div>

## At a glance

```python
from swatpy import SwatModel, rchOutputManipulator

model = SwatModel.initFromTxtInOut("path/to/TxtInOut", copy=True, target_dir="work")
model.enrichModelMeta()                          # simulation period from file.cio

model.setParameter("r__CN2__mgt", -0.1)          # CN2 * (1 - 0.1) in all .mgt files
model.setParameter("v__GW_DELAY__gw", 30.0)      # replace in all .gw files

model.swat_exec = "/path/to/swat2012"
model.run(silent=True)

reach = rchOutputManipulator(["FLOW_OUT"], [1], "skip", True, 0, model.working_dir, iprint="month")
flow = reach.outValues["FLOW_OUT"][1]
```

`swatpy` does not ship a SWAT2012 executable; it looks for one on the `PATH`, in the model
directory, or uses `model.swat_exec` explicitly.

## Package layout

| Module | Contents |
| --- | --- |
| `swatpy.SimManage` | `SwatModel` (create/load/run a model) and `parseParameterName` |
| `swatpy.FileEdit` | the input file manipulators (`.bsn`, `.gw`, `.mgt`, `.sub`, `.hru`, `.rte`, `.sol`, `file.cio`) |
| `swatpy.ReadOut` | the output readers (`rch`/`sub`/`hru`), plus `efficiency` and `fluxes` |

## Citing

If you use swatpy, please cite it via the Zenodo DOI
[10.5281/zenodo.6322023](https://doi.org/10.5281/zenodo.6322023), see also `CITATION.cff`.
