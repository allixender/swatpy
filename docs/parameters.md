# Parameters

`model.setParameter(name, value)` accepts SWAT-CUP style names of the form

```
<how>__<PARAM>__<ext>[__<hydgrp>__<soltext>__<landuse>__<subbsn>__<slope>]
```

- `<how>` — `v` (replace), `r` (relative, `x * (1 + value)`) or `a` (add);
- `<PARAM>` — the SWAT parameter name as used in the input file;
- `<ext>` — the file type (`bsn`, `gw`, `mgt`, `sub`, `hru`, `rte`, `sol`, `fileCio`).

`parseParameterName` splits such a name and returns `(how, PARAM, ext, qualifiers)`:

```python
from swatpy import parseParameterName
parseParameterName("r__CN2__mgt")        # ("*", "CN2", "mgt", [])
```

The SWAT-CUP qualifiers after the file extension (hydrologic group, soil texture, landuse,
subbasin, slope — e.g. `v__CANMX__hru______FRSD`) are parsed but **not** evaluated: such a
parameter is applied to all files of its type.

## File types and parameters

`model.getFileManipulators()` builds one manipulator per input file and groups them by
file type. The table lists the parameters preloaded for each type; every parameter in the
manipulator's `parInfo` is read lazily on first change, so names outside this list still
work.

### `.bsn` — basin

`SURLAG` `SFTMP` `SMTMP` `SMFMX` `SMFMN` `SNOCOVMX` `SNO50COV` `TIMP` `ESCO` `EPCO`

### `.gw` — groundwater

`GW_DELAY` `ALPHA_BF` `GW_REVAP` `GWQMN` `RCHRG_DP` `REVAPMN`

### `.sol` — soil (per layer)

`SOL_K` `SAND` `SILT` `CLAY` `ROCK` `SOL_CBN` `SOL_BD` `SOL_AWC` `SOL_CRK` `SOL_ZMX`

Soil parameters are lists over the profile horizons; `setParameter("a__SOL_AWC__sol", x)`
adds `x` to every layer. Urban (`URBN`) soils are skipped.

### `.hru` — HRU

`HRU_FR` `ESCO` `EPCO` `OV_N` `CANMX` `SLSUBBSN` `SLSOIL` `LAT_TTIME`

### `.rte` — main channel

`CH_N2` `CH_K2` `CH_S2`

### `.sub` — subbasin

`SUB_KM` `CH_L1` `CH_S1` `CH_W1` `CH_K1` `CH_N1` `CO2`

### `.mgt` — management

`CN2`

### `file.cio` — control

`NBYR` `IYR` `IPRINT` `NYSKIP`

## Relative vs. add vs. replace

The three change modes map to the manipulator operations `"*"`, `"+"` and `"s"`:

```python
model.setParameter("r__CN2__mgt", -0.1)     # value + value * (-0.1)
model.setParameter("a__SOL_AWC__sol", 0.02)  # value + 0.02
model.setParameter("v__GW_DELAY__gw", 30.0)  # 30.0
```

Changes are always computed from the values read when the manipulator was created, so
repeating the same `setParameter` call does not accumulate. Changes to several parameters
of the same file are all kept (even with a `finishChangePar()` in between).
