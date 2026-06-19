=============================
PowerPC Instruction Reference
=============================

This document covers the PowerPC instructions implemented in
``src/helpers/PowerPC.py``, targeting the Broadway CPU found in the
Nintendo Wii. All functions return 4 bytes in big-endian order, ready to
be patched directly into a Wii ISO.

Table of Contents
-----------------

-  `PowerPC Instruction Reference <#powerpc-instruction-reference>`__

   -  `Table of Contents <#table-of-contents>`__
   -  `Encoding Formats <#encoding-formats>`__

      -  `I-Form <#i-form>`__
      -  `B-Form <#b-form>`__
      -  `D-Form <#d-form>`__
      -  `X-Form <#x-form>`__
      -  `XO-Form <#xo-form>`__
      -  `M-Format <#m-format>`__

   -  `Options <#options>`__

-  `Glossary <#glossary>`__

-  `References <#references>`__

Encoding Formats
----------------

In following tables, header are bits numbers (included on both side). A ``/`` is a bit not used.

I-Form
~~~~~~

===== ====== == ==
0 - 5 6 - 29 30 31
===== ====== == ==
OPCD  LI     AA LK
===== ====== == ==

B-Form
~~~~~~

===== ====== ======= ======= == ==
0 - 5 6 - 10 11 - 15 16 - 29 30 31
===== ====== ======= ======= == ==
OPCD  BO     BI      BD      AA LK
===== ====== ======= ======= == ==

D-Form
~~~~~~

===== ======== ======= =====
0 - 5 6 - 10   11 - 15 16 31
===== ======== ======= =====
OPCD  RT       RA      D
OPCD  RT       RA      SI
OPCD  RS       RA      S
OPCD  RS       RA      UI
OPCD  BF / L:1 RA      SI
OPCD  BF / L:1 RA      UI
OPCD  TO       RA      SI
OPCD  FRT      RA      D
OPCD  FRS      RA      D
===== ======== ======= =====

X-Form
~~~~~~

There are 32 subforms of X-form.

===== ====== ======= ======= ===== ==
0 - 5 6 - 10 11 - 15 16 - 20 21-30 31
===== ====== ======= ======= ===== ==
OPCD  RT     RA      RB      XO    /
===== ====== ======= ======= ===== ==

Sometimes:

* RT is:
    * TO
    * FRT
    * BT
    * BF / L
    * BF //
    * /// TH
    * /// L
* RA is:
    * / SR
    * /////
    * /// L
    * FRA
    * BFA //
* RB is:
    * NB
    * /////
    * FRB
    * U /
* The last bit is:
    * RC

XO-Form
~~~~~~~

===== ====== ======= ======= == ===== ==
0 - 5 6 - 10 11 - 15 16 - 20 21 22-30 31
===== ====== ======= ======= == ===== ==
OPCD  RT     RA      RB      OE XO    RC
OPCD  RT     RA      RB      /  XO    RC
OPCD  RT     RA      /////   OE XO    RC
===== ====== ======= ======= == ===== ==

M-Format
~~~~~~~~

===== ====== ======= ======= == ===== ==
0 - 5 6 - 10 11 - 15 16 - 20 21 22-30 31
===== ====== ======= ======= == ===== ==
OPCD  RS     RA      RB      MB ME    RC
OPCD  RS     RA      SH      MB ME    RC
===== ====== ======= ======= == ===== ==

Options
-------

TODO: need to find a way to properly explain BO. M = 0 if 64-bit mode or 32 in 32-bit mode

BO
~~

===== ========== ============================
BO    Operations Branch if (after operations)
===== ========== ============================
0000z CTR - 1    CTRM:63 != 0 AND CRBI = 0
0001z CTR - 1    CTRM:63 == 0 AND CRBI = 0
001at            CRBI = 0
0100z CTR - 1    CTRM:63 != 0 AND CRBI = 1
0101z CTR - 1    CTRM:63 == 0 AND CRBI = 1
011at            CRBI = 1
1a00t CTR - 1    CTRM:63 != 0
1a01t CTR - 1    CTRM:63 == 0
1z1zz            Always
===== ========== ============================

-  *z* means that bit is ignored
-  *a* and *t* are for hints. (For performance purposes)

== ===========================
at Hint
== ===========================
00 No hint
01 Reserved
10 Very likely to NOT be taken
11 Very likely to be taken
== ===========================

Glossary
--------

A lot of this are from the PowerPC User Instruction (see References for
the link)

-  **AA**: Absolute Address bit

   -  0: Immediate field represents relative address to the current
      instruction address.
   -  1: Immediate field represents absolute address

-  **BC**: Branch Conditional
-  **BD**: Immediate field used to specify a 14-bit signed two’s
   complement branch displacement which is concatenated on the right
   with 0b00 and signextended to 64 bits.
-  **BF**: Field used to specify one of the CR fields or FPSCR fields
-  **BI**: Used to specify a bit in the CR to be tested by a BC
-  **BO**: Branch options for the condition. See `in options <#bo>`__
-  **CR**: Condition register
-  **CTR**: Count register
-  **FPR**: Floating-Point Registers. 32 registers. 64 bits each.
-  **FPSCR**: Floating-Point Status and Control Register (basically for
   exceptions)
-  **FRS**: Field to specify a FPR to be used as a source (Floating
   Register Source)
-  **FRT**: Field to specify a FPR to be used as a target (Floating
   Register Target)
-  **GPR**: General Purpose Register: 32 registers. 64 bits each.
-  **L**: Used by the Synchronize instruction
-  **LK**: LINK bit:

   -  0: Do not set the link register
   -  1: The address of the instruction following the Branch is placed
      into the Link register

-  **MB/ME**: A mask of 64 bits with MB and ME fields
-  **OE**: To enable settings OV and SO in the XER.
-  **OV**: Overflow
-  **OPCD**: Primary opcode field
-  **RA**: Used to spicy a GPR to be used as a source or a target
-  **RB**: Used to spicy a GPR to be used as a source
-  **Rc**: RECORD bit.

   -  0: Do not alter the CR
   -  1: Set CR Field 0 or Field 1. See `in options <#condition-register>`__

-  **RS**: Register Source
-  **RT**/**RD**: Register Target/Register Destination
-  **SH**: Specify a shift amount
-  **SO**: Summary Overflow
-  **XER**: Fixed-Point Exception Register
-  **XO**: Extended opcode field

References
----------

-  `Fenixfox (incredible) <https://fenixfox-studios.com/manual/powerpc/index.html>`__
-  `PowerPC User Instruction Set Architecture (awesome) <https://math-atlas.sourceforge.net/devel/assembly/ppc_isa.pdf>`__
-  `YAHDFPPC (Yet another HTML doc for PowerPC) <http://ps-2.kev009.com/wisclibrary/aix52/usr/share/man/info/en_US/a_doc_lib/aixassem/alangref/alangref02.htm#wq2793>`__
