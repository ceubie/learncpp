Project: a container for the source files, data, and IDE/compiler/linker settings that produce one program (executable, library, etc.). One project = one program. Create a new project for each new program. Project files are IDE-specific.

Console project: a text-only program that reads the keyboard and writes to a terminal. No GUI. That is what this course uses.

Workspace / solution: a container that can hold one or more related projects (Visual Studio says “solution”; many other IDEs say “workspace”). While learning, make a new workspace/solution per program.

Hello world is the traditional first program. Name the primary file `main.cpp`. Turn precompiled headers off for these small programs.

Build-menu vocab (object files may be cached so unchanged files are not recompiled):
- Build: compile modified files, then link into an executable. Does nothing if nothing changed.
- Clean: delete cached object files and executables so the next build recompiles everything.
- Rebuild: clean, then build.
- Compile: recompile a single file. Does not link and does not produce an executable.
- Run / start: execute the last build. Some IDEs (Visual Studio) build first; others (Code::Blocks) just run whatever is already there.

People say “compile the program” informally; in the IDE you usually choose Build or Run.

If the console flashes and closes, the IDE closed the window when the program ended. Prefer “Start Without Debugging.” Avoid `system("pause")` — it is not portable. Antivirus can also block a new executable; excluding the project folder from scans is often enough.
