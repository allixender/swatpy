# docker/Dockerfile: SWAT2012 (gfortran build) as a run-anything toolbox image.
# Build context is this directory (it provides the Makefile and the gfortran patch script):
#   podman build -t swat2012:rev692 -t swat2012:latest docker/
FROM docker.io/library/ubuntu:24.04 AS build
RUN apt-get update && apt-get install -y --no-install-recommends \
        gfortran make git ca-certificates && rm -rf /var/lib/apt/lists/*
# upstream tag or branch of https://github.com/swat-model/swat2012 (rev.692 = SWAT2012 revision 692)
ARG SWAT_REF=rev.692
RUN git clone --depth 1 -b ${SWAT_REF} https://github.com/swat-model/swat2012 /src
COPY Makefile patch_gfortran.sh /src/src/
WORKDIR /src/src
RUN sh patch_gfortran.sh && make -j"$(nproc)"

FROM docker.io/library/ubuntu:24.04
ARG SWAT_REF=rev.692
LABEL org.opencontainers.image.title="swat2012" \
      org.opencontainers.image.version="${SWAT_REF}" \
      org.opencontainers.image.description="SWAT2012 ${SWAT_REF} built with gfortran, for use with swatpy" \
      org.opencontainers.image.source="https://github.com/allixender/swatpy" \
      org.opencontainers.image.base.name="docker.io/library/ubuntu:24.04" \
      org.opencontainers.image.licenses="GPL-3.0-or-later" \
      swat2012.ref="${SWAT_REF}"
RUN apt-get update && apt-get install -y --no-install-recommends libgfortran5 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /src/src/swat2012 /usr/local/bin/swat2012
WORKDIR /model
ENTRYPOINT ["swat2012"]
