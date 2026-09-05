1. When making changes to your code, make behavioral changes OR structural changes, and then retest for correctness. Making behavioral and structural changes at the same time tends to lead to more errors as well as errors that are harder to find.

2. Use a static analysis tool on your programs to help find areas where your code is non-compliant with best practices.

For Visual Studio users

Visual Studio 2019 onward comes with a built-in static analysis tool. You can access it via Build > Run Code Analysis on Solution (Alt+F11).

Some commonly recommended static analysis tools include:

Free:

clang-tidy
cpplint
cppcheck (already integrated into Code::Blocks)
SonarLint
Most of these have extensions that allow them to integrate into your IDE. For example, Clang Power Tools extension.

Paid (may be free for Open Source projects):

Coverity
SonarQube