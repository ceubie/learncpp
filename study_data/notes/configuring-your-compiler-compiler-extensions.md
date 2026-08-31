Compiler extensions are extra, compiler-specific behaviors that are not part of standard C++. They are often on by default. Code that relies on them may not compile (or may not run correctly) on another compiler.

They are never required. Turn them off so you learn real C++ and stay portable.

Typical switches:
- Visual Studio: Conformance mode Yes (`/permissive-`), All Configurations
- GCC / Clang / Code::Blocks: `-pedantic-errors`

These settings are per-project. Set them on every new project, or save a project template that already has them.
