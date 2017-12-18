.PHONY: test unit-test functional-test

CXXFLAGS = \
	--std=c++11 \
	-Wall \
	-Wno-deprecated-declarations \
	-Werror \
	$(NIX_CFLAGS_COMPILE)

unittests: main.o
	$(CXX) $^ -o $@

unit-test: unittests
	./unittests

functional-test:
	$(SHELL) test.sh

test: unit-test functional-test

clean:
	$(RM) *.o unittests