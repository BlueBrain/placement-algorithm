.PHONY: clean

all: scorePlacement

scorePlacement: main.cpp
	g++ --std=c++11 -lboost_program_options -lboost_filesystem $< -o $@

test: scorePlacement
	cd tests && bash test.sh

clean:
	rm -f scorePlacement
