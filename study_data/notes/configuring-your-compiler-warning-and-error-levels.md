A program that violates the language rules is ill-formed. Compilers report problems as diagnostics.

- Diagnostic error (compile error): compilation stops.
- Diagnostic warning: compilation continues; the issue is ignored.

Compilers do not always agree on error vs warning for the same issue. The message usually includes a file and line; the real problem may be on that line or an earlier one.

The compiler may also warn about code that is legal but looks wrong. Fix warnings as you get them so a serious one is not lost in the noise. The linker can emit errors too.

Turn warning levels up while learning. Also enable “treat warnings as errors” so a warning fails the build (`/WX` on MSVC, `-Werror` on GCC/Clang).

Do not use MSVC `/Wall` — it floods you with standard-library warnings. `/W4` is the usual VS setting.
