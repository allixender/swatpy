# SWAT2012 container

A podman/docker image with the SWAT2012 executable (gfortran build of
[swat-model/swat2012](https://github.com/swat-model/swat2012), tag `rev.692`, which reports itself as
"Rev. 693"). The image is used like the executable: the entrypoint is `swat2012`, the working directory is
`/model`.

## Build

```sh
podman build -t swat2012:rev692 -t swat2012:latest docker/
```

- The build context is `docker/` (it holds the SWAT `Makefile` and `patch_gfortran.sh`), not the Dockerfile.
- Native build: arm64 on Apple Silicon (about a minute), amd64 on x86. Use `--platform linux/amd64` for an
  x86 image (slow under qemu; this is what matches the GitHub runners). Make sure the cached
  `ubuntu:24.04` base has the platform you want, `podman pull --platform linux/arm64 ubuntu:24.04`.
- Another upstream revision: `--build-arg SWAT_REF=<tag or branch>`.
- `patch_gfortran.sh` makes the Intel-Fortran source compile with gfortran (interface/name clash with
  `module parm` in seven files plus `HQDAV.f90`, mixed string lengths in `header.f`). Numerics are not touched.

## Run

```sh
cd path/to/TxtInOut
podman run --rm --userns=keep-id -v "$PWD":/model:Z swat2012
```

`docker/swat2012-podman` does exactly this; put it on the `PATH` or use it by absolute path:

```sh
SWAT2012_IMAGE=localhost/swat2012:rev692 docker/swat2012-podman   # image override, default :latest
```

`--userns=keep-id` keeps the output files owned by you (rootless podman), `:Z` relabels the mount on
SELinux hosts and is ignored elsewhere.

## Use from swatpy

`SwatModel.run()` starts `model.swat_exec` with `cwd=working_dir`, so the wrapper sees the right `$PWD`:

```python
model.swat_exec = "/abs/path/to/docker/swat2012-podman"
model.is_runnable()
model.run()
```

The `swat` tests can run through it too: `SWATPY_SWAT_EXE=$PWD/docker/swat2012-podman SWATPY_TEST_DOWNLOAD=1 pytest -m swat`.

## Caveats

- The build is SWAT2012 rev 693 (gfortran), not the rev 637 executable the integration tests were written
  for. The output has 58 instead of 49 reach columns, so three tests in `tests/test_swat_demo.py`
  (`test_daily_readout_matches_tokens_and_metadata` for rch and sub, `test_parameter_changes_have_expected_effect`)
  fail with this image; the other `swat` tests pass. Keep CI on the rev 637 binary until the readers
  handle the newer layout.
- Every run starts a container, which adds overhead that accumulates in calibration with thousands of runs. There, run spotpy inside a container or use a native executable.
