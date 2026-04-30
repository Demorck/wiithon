# PowerPC Instruction Reference

This document covers the PowerPC instructions implemented in `src/helpers/PowerPC.py`, targeting the Broadway CPU found in the Nintendo Wii. All functions return 4 bytes in big-endian order, ready to be patched directly into a Wii ISO.

---

## Table of Contents

---

## Encoding Formats

### I-Form
| 0 - 5 | 6 - 29 |  30  |  31  |
|:-----:|:------:|:----:|:----:|
| OPCD  |   LI   |  AA  |  LK  |


### B-Form
| 0 - 5 | 6 - 10 | 11 - 15 | 16 - 29 | 30 | 31 |
|:-----:|:------:|:-------:|:-------:|----|----|
| OPCD  |   BO   |   BI    |   BD    | AA | LK |

### D-Form
| 0 - 5 |   6 - 10   | 11 - 15 | 16 31 |
|:-----:|:----------:|:-------:|:-----:|
| OPCD  |     RT     |   RA    |   D   |
| OPCD  |     RT     |   RA    |  SI   |
| OPCD  |     RS     |   RA    |   S   |
| OPCD  |     RS     |   RA    |  UI   |
| OPCD  | BF /:1 L:1 |   RA    |  SI   |
| OPCD  | BF /:1 L:1 |   RA    |  UI   |
| OPCD  |     TO     |   RA    |  SI   |
| OPCD  |    FRT     |   RA    |   D   |
| OPCD  |    FRS     |   RA    |   D   |

---

## Options
#### BO 
A Heading in this SO entry!

---

# Glossary
A lot of this are from the PowerPC User Instruction (see References for the link)

- **AA**: Absolute Address bit
  - 0: Immediate field represents relative address to the current instruction address.
  - 1: Immediate field represents absolute address
- **BC**: Branch Conditional
- **BD**: Immediate field used to specify a 14-bit signed two's complement branch displacement which is concatenated on the right with 0b00 and signextended to 64 bits.
- **BF**: Field used to specify one of the CR fields or FPSCR fields
- **BI**: Used to specify a bit in the CR to be tested by a BC
- **BO**: Branch options for the condition. See [in options](#bo-)
- **FPR**: Floating-Point Registers. 32 registers. 64 bits each.
- **FPSCR**: Floating-Point Status and Control Register (basically for exceptions)
- **GPR**: General Purpose Register: 32 registers. 64 bits each.
- **LK**: LINK bit:
  - 0: Do not set the link register
  - 1: The address of the instruction following the Branch is placed into the Link register
- **OPCD**: Primary opcode field
- **RS**: Register Source
- **RT**/**RD**: Register Target/Register Destination

---

# References
- [Fenixfox (incredible)](https://fenixfox-studios.com/manual/powerpc/index.html)
- [PowerPC User Instruction Set Architecture (awesome)](https://math-atlas.sourceforge.net/devel/assembly/ppc_isa.pdf)
- [YAHDFPPC (Yet another HTML doc for PowerPC)](http://ps-2.kev009.com/wisclibrary/aix52/usr/share/man/info/en_US/a_doc_lib/aixassem/alangref/alangref02.htm#wq2793)