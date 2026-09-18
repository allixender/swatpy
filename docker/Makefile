FC       = gfortran
FFLAGS   = -O2 -std=legacy -ffixed-line-length-none -ffree-line-length-none -fno-range-check

# main.f includes modparm.f (the module parm owner), so modparm.f must NOT be
# compiled standalone; main.f must build first so it emits parm.mod for the
# ~295 units that do `use parm`.
SRCS_F   = $(filter-out main.f modparm.f, $(wildcard *.f))
SRCS_F90 = $(wildcard *.f90)
OBJS     = $(SRCS_F:.f=.o) $(SRCS_F90:.f90=.o)

swat2012: main.o $(OBJS)
	$(FC) $(FFLAGS) -o $@ main.o $(OBJS)

main.o: main.f modparm.f
	$(FC) $(FFLAGS) -c main.f

$(OBJS): main.o

%.o: %.f
	$(FC) $(FFLAGS) -c $<

%.o: %.f90
	$(FC) $(FFLAGS) -c $<

.PHONY: clean
clean:
	rm -f *.o *.mod swat2012
