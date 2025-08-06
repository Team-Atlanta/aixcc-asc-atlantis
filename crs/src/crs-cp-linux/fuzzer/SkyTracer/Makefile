OUT=$(CURDIR)/out
CPU=`nproc`

all: out/Makefile.ninja
	make -C $(OUT) -j$(CPU)

out/Makefile.ninja:
	mkdir -p $(OUT)
	cd $(OUT) && $(CURDIR)/qemu/configure --target-list=x86_64-softmmu

clean:
	rm -rf out
