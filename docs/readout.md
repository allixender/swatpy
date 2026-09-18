# Output readers

The readers in `swatpy.ReadOut` parse the fixed-width `output.rch`, `output.sub` and
`output.hru` files written by SWAT. They derive the value column positions from the header
line, so a reduced selection of printed variables in `file.cio` is read correctly, and they
drop the yearly summary rows (monthly output) and the closing average-annual row.

## Reading time series

```python
from swatpy import rchOutputManipulator

reach = rchOutputManipulator(
    ["FLOW_OUT", "SED_OUT"], [1, 2],
    "skip", True, 0,
    working_dir,
    iprint="month",
)
flow_reach1 = reach.outValues["FLOW_OUT"][1]   # [float, ...]
```

`outValues` is a nested dictionary `variable -> area -> list of values`. `readAreaSizes`
returns the reach / subbasin / HRU area, and `readValues` returns the time series. The
`iprint` argument must match the print code in `file.cio` (`"month"` / `0`, `"day"` / `1`,
`"year"` / `2`).

The three readers share the same interface and differ only in column layout:

| Reader | Source | Area id | `valueStart` | `valueWidth` |
| --- | --- | --- | --- | --- |
| `rchOutputManipulator` | `output.rch` | reach | 37 | 12 |
| `subOutputManipulator` | `output.sub` | subbasin | 34 | 10 |
| `hruOutputManipulator` | `output.hru` | HRU | 44 | 10 |

A few fields are one character wider than their label (`sub` `CHOLA`, `hru` `BACTP`/`BACTLP`);
the readers widen those columns so the following columns stay aligned.

## Writing files

Instead of `"skip"`, `method` can write individual and/or summed values plus statistics:

```python
rchOutputManipulator(["FLOW_OUT"], [1], "sum & indi", False, 0, working_dir, iprint="month")
```

With `"sum"` the per-area values are scaled by area (`mm/d` on `km²` to `m³/s`) and summed
over the areas. Statistics are mean, median and variance (the lag-1 autocorrelation is
commented out).

## Efficiency

`efficiency` compares a simulated reach series against observations from a semicolon-
separated file:

```python
from swatpy import efficiency

eff = efficiency("FLOW_OUT", 1, "observed.txt", fileColumn=2, daysSkip=365,
                 working_dir=working_dir, iprint="day")
nse = eff.nash()   # Nash-Sutcliffe efficiency
agr = eff.agr()    # agreement index (d)
```

Observations equal to `nodata` (default `-9999`) are masked out of both metrics.

## Fluxes

`fluxes` sums a subbasin variable from `output.sub` over the subbasins, scaled by area to
`m³/s`, and returns the mean over the remaining time series:

```python
from swatpy import fluxes

f = fluxes("WYLD", [1, 2, 3], daysSkip=365, working_dir=working_dir, iprint="day")
mean = f.result()
```
