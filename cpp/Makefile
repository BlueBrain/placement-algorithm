# -Wno-deprecated-declarations: Boost still uses auto_ptr somewhere
CXXFLAGS = \
	--std=c++11 \
	-Wall \
	-Wno-deprecated-declarations \
	-Werror \
	$(NIX_CFLAGS_COMPILE)

LDFLAGS = \
	-lboost_program_options \
	-lboost_filesystem \
	#TODO: $(NIX_LDFLAGS)

all: scorePlacement

scorePlacement: main.o
	$(CXX) $(LDFLAGS) $< -o $@

test: scorePlacement
	$(MAKE) -C tests $@

clean:
	$(MAKE) -C tests $@
	$(RM) *.o scorePlacement

install: all
	install -D -t $(PREFIX)/bin scorePlacement
