Steps 4–7 of the development pipeline:

4. Compile. The compiler walks each `.cpp` file, checks that the code follows C++ rules (errors abort compilation), and translates it to machine instructions in an object file (`.o` or `.obj`, same base name as the source file). One `.cpp` → one object file.

5. Link. The linker combines object files into the output (usually an executable). It resolves cross-file references (use in one file, definition in another), links libraries, and aborts with a linker error if something cannot be connected.

Libraries are packaged precompiled code for reuse.
- C++ Standard Library (“the standard library”): ships with C++. iostream (console input/output) is a commonly used part. Linkers usually link it by default.
- Third-party libraries: created by others, used when the standard library has no equivalent (e.g. playing sound).

Building is the full source-to-executable process. A build is a specific executable produced by that process.

6–7. Testing checks whether the program behaves as expected. Debugging is finding and fixing errors when it does not.

An IDE (integrated development environment) bundles editor, compiler, linker, and debugger.
