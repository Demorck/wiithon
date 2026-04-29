# PowerPC Instruction Reference

This document covers the PowerPC instructions implemented in `src/helpers/PowerPC.py`, targeting the Broadway CPU found in the Nintendo Wii. All functions return 4 bytes in big-endian order, ready to be patched directly into a Wii ISO.

---

## Table of Contents

---

## Encoding Formats


# Glossary
A lot of this are from the PowerPC User Instruction (see References for the link)

- **BD**: Immediate field used to specify a 14-bit signed two's complement branch displacement which is concatenated on the right with 0b00 and signextended to 64 bits.
- **FPR**: Floating-Point Registers. 32 registers. 64 bits each.
- **GPR**: General Purpose Register: 32 registers. 64 bits each.

---

# References
- [Fenixfox (incredible)](https://fenixfox-studios.com/manual/powerpc/index.html)
- [PowerPC User Instruction Set Architecture (awesome)](https://math-atlas.sourceforge.net/devel/assembly/ppc_isa.pdf)
- [YAHDFPPC (Yet another HTML doc for PowerPC)](http://ps-2.kev009.com/wisclibrary/aix52/usr/share/man/info/en_US/a_doc_lib/aixassem/alangref/alangref02.htm#wq2793)