# docker/swat2012/Containerfile
FROM docker.io/library/ubuntu:24.04 AS build
RUN apt-get update && apt-get install -y --no-install-recommends \
        gfortran make git ca-certificates && rm -rf /var/lib/apt/lists/*
ARG SWAT_REF=main
RUN git clone --depth 1 -b ${SWAT_REF} https://github.com/swat-model/swat2012 /src
COPY Makefile /src/src/Makefile
WORKDIR /src/src
RUN make

FROM docker.io/library/ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends libgfortran5 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /src/src/swat2012 /usr/local/bin/swat2012
WORKDIR /model
ENTRYPOINT ["swat2012"]
