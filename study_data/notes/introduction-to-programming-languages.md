A computer program is a sequence of instructions that tells a computer what to do, in order. Writing one is programming. Running / executing / launching means the computer is performing those instructions.

Hardware is the physical machine (CPU, memory, input devices, storage). Software is the programs that run on it. A platform is a compatible set of hardware plus software (OS, etc.) that programs run on. Using platform services makes a program dependent on that platform.

Portable programs transfer to another platform easily. Porting is the work of making a program run on a different platform. Cross-platform means designed to run on multiple platforms.

Language levels
- Machine language / machine code: the only language a CPU understands. An instruction set (ISA) is the set of instructions a CPU family understands. Machine code is bits (0s and 1s) and is not portable across CPU families.
- Assembly: a more human-readable form of machine language (mnemonics, named registers). An assembler translates assembly to machine code. Still low-level and architecture-specific.
- High-level languages (C, C++, Java, …): abstract away the CPU. Easier to read/write, more portable, fewer instructions for the same work. C++ is sometimes called mid-level because you can work at both low and high abstraction.

Translation
- A compiler translates source (usually high-level) into another language (usually machine code) and can produce a standalone executable. The compiler does not need to be installed to run that executable.
- An interpreter executes source directly. More flexible, slower, and the interpreter must be present wherever the program runs.

C++ is usually compiled.

Callouts in these tutorials
- Rule: you must do this; otherwise the program generally will not work.
- Best practice: you should do this (conventional or better).
- Warning: you should not do this; it usually leads to unexpected results.
