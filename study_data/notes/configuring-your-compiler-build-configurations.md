A build configuration (also called a build target) is a named set of project settings: output name, search paths, whether to keep debug info, how hard to optimize, and so on.

IDEs usually create two:
- Debug: no (or almost no) optimization, includes debugging information. Larger and slower, much easier to debug. This should be the active configuration while you write programs.
- Release: optimized for size/performance, debug info stripped. Use this to ship a program or to measure performance.

Visual Studio may also have separate configs per platform (x86 32-bit vs x64 64-bit).

When you change a project setting, change it in all configurations unless you have a reason not to.
