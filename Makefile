# Installation prefix
PREFIX = /usr/local

all install test clean:
	$(MAKE) -C cpp $@
	$(MAKE) -C pyspark $@
