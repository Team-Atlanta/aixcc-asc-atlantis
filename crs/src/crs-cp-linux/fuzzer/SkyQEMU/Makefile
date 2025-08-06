OUT=$(CURDIR)/out
SYMCC=$(CURDIR)/symcc
CPU=`nproc`

all: out/Makefile.ninja
	make -C libsym
	make -C $(OUT) -j$(CPU)

out/Makefile.ninja:
	mkdir -p $(OUT)
	cd $(OUT) && $(CURDIR)/qemu/configure --target-list=x86_64-softmmu --libsym=$(CURDIR)/libsym

clean:
	rm -rf out
