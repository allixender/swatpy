#!/bin/sh
# Make the upstream SWAT2012 source (written for Intel Fortran) compile with gfortran.
# Run in the src/ directory. The sources are patched in place, only what gfortran rejects.
set -eu

# 1. modparm.f declares an INTERFACE for some external procedures, and the files defining
#    them do `use parm` themselves. Intel accepts that, gfortran errors with "'x' of module
#    'parm' is also the name of the current program unit". Rename the clashing import.
for f in atri layersplit ndenit regres rsedaa tair vbl; do
    sed -i -E "s/^[[:space:]]*use[[:space:]]+parm[[:space:]]*\$/      use parm, ifc_${f} => ${f}/I" "${f}.f"
done
sed -i -E "s/^[[:space:]]*use[[:space:]]+parm[[:space:]]*\$/      use parm, ifc_hqdav => hqdav/I" HQDAV.f90

# 2. header.f: the heading constructors mix string lengths (11..13), which Intel pads to the
#    declared character(len=13). Give the constructors an explicit type-spec to do the same.
sed -i -E 's/^([[:space:]]+hed[a-z]+[[:space:]]*=[[:space:]]*\(\/)/\1 character(len=13) :: /I' header.f

# fail loudly if a patch did not apply
grep -q "ifc_" atri.f HQDAV.f90
grep -q "character(len=13) ::" header.f
