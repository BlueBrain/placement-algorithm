.PHONY: test unit-test functional-test

CXXFLAGS+= \
	--std=c++11 \
	-Wall \
	-Wno-deprecated-declarations \
	-Werror

unittests: main.o test_lib.o
	$(CXX) $(LDFLAGS) $^ -o $@

unit-test: unittests
	./unittests

functional-test:
	$(SHELL) test.sh

test: unit-test functional-test

clean:
	$(RM) *.o unittests
