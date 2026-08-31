Runtime
- Console blinks and closes: the program finished and the window went away. Run without debugging, or wait for a key at the end of `main`. Do not use `system("pause")`.
- Window but no output: antivirus/malware scanner may be blocking the exe.
- Compiles but behaves wrong: debug it (chapter 3).

Compile / link
- Unresolved external `_main` or `_WinMain`: the linker cannot find `main`. Check the name, that the file containing `main` is actually in the project, and that you created a console project (not a GUI/WinMain project).
- `main` already defined: a program may have only one `main`. Remove the extras.
- Cannot open the `.exe` for writing (VS: LNK1168): the program is still running, or something (often antivirus) has the file locked. Close it and rebuild.
- `cin` / `cout` / `endl` undeclared: `#include <iostream>` and prefix with `std::`.
- `end1` undeclared: that is a lowercase L in `endl`, not the digit 1. Use a programming font.

Newer language features “don’t work”: the compiler is old, or it is defaulting to an older language standard (see 0.12).

When stuck: search the exact error in quotes (drop filenames and line numbers), then ask a Q&A site with OS and IDE included.
