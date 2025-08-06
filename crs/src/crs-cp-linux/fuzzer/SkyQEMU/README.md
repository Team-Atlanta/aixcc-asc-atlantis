# SkyQEMU
Rewritten SymQEMU based on qemu-8.1.4

# How to use
- Kernel must be compiled without KASAN

# TODO
- [ ] Check whether we can remove symbolic modelling for `sym_load_host`, `sym_store_host`, and `sym_notify_block`.
- [ ] Check whether we can remove address translation between guest and host in `sym_load_guest` and `sym_store_guest`.
- [ ] Optimize function hooking
- [ ] Parse symbol tables by using QEMU internal instead of using readelf
- [ ] Sanitizer
  - Out-of-bound access
  - double fetch
- [ ] Distinguish assertion and constraint
- [ ] Revisit copy_from_user and copy_to_user..
  - Handle the given address is not user address.
