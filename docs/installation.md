# Installation

## From PyPI

```sh
pip install swatpy                  # numpy and chardet only
pip install "swatpy[calibration]"   # plus spotpy, scipy and pandas for the calibration scripts
pip install "swatpy[mpi]"           # plus mpi4py for parallel spotpy samplers
```

swatpy requires Python 3.10 or newer.

## A SWAT2012 executable

`swatpy` does not include a SWAT2012 executable. When a model is created or loaded,
`is_runnable()` looks for `model.swat_exec` (default `swat_64rel.exe`):

1. on the `PATH` (or as a path), via `shutil.which`;
2. in the model working directory.

If an executable is found, `model.swat_exec` is set to its absolute path. `run()` starts
`os.path.join(model.working_dir, model.swat_exec)`, so an absolute path is used as it is and a
bare name refers to the working directory. Set the executable explicitly and check it:

```python
model.swat_exec = "/path/to/swat2012"
model.is_runnable()   # 1 if an executable was found
```

### As a podman image

No executable at hand (macOS, Windows)? `docker/` builds one into a container image, see
`docker/README_docker.md`:

```sh
podman build -t swat2012:rev692 -t swat2012:latest docker/
```

```python
# wrapper script: podman run --rm -v $PWD:/model swat2012
model.swat_exec = "/path/to/swatpy/docker/swat2012-podman"
```

## From source

```sh
git clone https://github.com/allixender/swatpy
cd swatpy
pip install -e ".[dev]"
```

The `[dev]` extra adds pytest, build, twine and ruff. The `[docs]` extra adds
MkDocs and mkdocstrings (see [Development](development.md)).
