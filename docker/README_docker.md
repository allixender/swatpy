Usage:

- `podman build -t swat2012 docker/Dockerfile` builds a native arm64 image on your Mac.
- Adding `--platform linux/amd64` builds an x86 image instead, matching the GitHub CI runners.
- To run a model: `podman run --rm -v $PWD/TxtInOut:/model swat2012`.

Things you should decide when you picks this up:

- Calling it from swatpy: `SwatModel.run()` expects a local executable. The simplest option is a small wrapper script, e.g. `swat2012-podman running podman run --rm -v "$PWD":/model swat2012`, set as `swat_exec`. `run()` already chdirs into the working directory, so `$PWD` resolves correctly.
- Intel-only code: some SWAT2012 revisions use Intel-only modules or intrinsics (such as ifport). If the repo hasn't already patched them for gfortran, the build will need small patches.
- Numerical differences: a `gfortran` build may differ slightly from the `rev637` binary used in the CI integration test. Either keep CI on the `rev637` binary or switch CI to this