CPU=`nproc`

all: build/libSymRuntime.so
	ninja

z3:
	wget https://github.com/Z3Prover/z3/archive/refs/tags/z3-4.12.5.zip -O z3.zip
	unzip z3.zip
	rm z3.zip
	mv z3-z3-4.12.5 z3

z3/build/z3: z3
	mkdir z3/build
	cd z3/build && cmake -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release ../
	cd z3/build && make -j$(CPU)

build/libSymRuntime.so: z3/build/z3 
	cmake -G Ninja -DZ3_DIR=$(CURDIR)/z3/build
	ninja

clean:
	rm -rf cmake_install.cmake CMakeCache.txt CMakeFiles build.ninja build rules.ninja
