# -Wno-deprecated-declarations: Boost still uses auto_ptr somewhere
CXXFLAGS+= \
	--std=c++11 \
	-Wall \
	-Wno-deprecated-declarations \
	-Werror

LDLIBS = \
	-lboost_filesystem \
	-lboost_program_options

all: scorePlacement

scorePlacement: main.o
	$(CXX) $(LDFLAGS) $(LDLIBS) $< -o $@

test: scorePlacement
	$(MAKE) -C tests $@

clean:
	$(MAKE) -C tests $@
	$(RM) *.o scorePlacement

install: all
	install -D -t $(PREFIX)/bin scorePlacement
