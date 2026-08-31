You can ask the compiler which language standard it is actually using. The portable query is the `__cplusplus` macro, which expands to a long date code (`201703L` for C++17, `202002L` for C++20, etc.).

Visual Studio is non-conforming here unless you set an extra flag. On MSVC 2015+, use `_MSVC_LANG` instead of `__cplusplus`.

If the printed standard is not the one you think you selected: check the project settings (many IDEs store this per-project, not globally), and confirm the IDE is reading the config file you edited.

A preview / pre-release standard is fine while learning. Some upcoming features may be missing, incomplete, buggy, or still changing.
