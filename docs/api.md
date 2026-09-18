# API reference

The public API is exported from the top-level `swatpy` package:

```python
from swatpy import (
    SwatModel, parseParameterName,
    fileCioManipulator, bsnManipulator, subManipulator, hruManipulator,
    solManipulator, gwManipulator, mgtManipulator, rteManipulator,
    rchOutputManipulator, subOutputManipulator, hruOutputManipulator,
    efficiency, fluxes,
)
```

## Simulation management

::: swatpy.SimManage.SwatModel
    options:
      members:
        - initFromTxtInOut
        - loadModelFromDirectory
        - run
        - getFileManipulators
        - reloadFileManipulators
        - setParameter
        - enrichModelMeta
        - is_runnable
        - guess_model_text_encoding

::: swatpy.SimManage.parseParameterName

## Input file manipulators

::: swatpy.FileEdit.InputFileManipulator

::: swatpy.FileEdit.fileCioManipulator
    options:
      members: false

::: swatpy.FileEdit.bsnManipulator
    options:
      members: false

::: swatpy.FileEdit.gwManipulator
    options:
      members: false

::: swatpy.FileEdit.mgtManipulator
    options:
      members: false

::: swatpy.FileEdit.subManipulator
    options:
      members: false

::: swatpy.FileEdit.hruManipulator
    options:
      members: false

::: swatpy.FileEdit.rteManipulator
    options:
      members: false

::: swatpy.FileEdit.solManipulator

::: swatpy.FileEdit.solManipulationCorrection
    options:
      members: false

::: swatpy.FileEdit.solManipulationCheck
    options:
      members: false

## Output readers

::: swatpy.ReadOut.OutputFileManipulator

::: swatpy.ReadOut.rchOutputManipulator
    options:
      members: false

::: swatpy.ReadOut.subOutputManipulator
    options:
      members: false

::: swatpy.ReadOut.hruOutputManipulator
    options:
      members: false

::: swatpy.ReadOut.efficiency

::: swatpy.ReadOut.fluxes
