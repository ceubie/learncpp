Compilers default to some language standard, often an older one (C++14 is common), not the newest. You usually have to pick the standard yourself. Change it in all build configurations.

Informal names use the publication year: C++11, C++14, C++17, C++20, C++23. Early-in-development names look like C++2a / C++2b. C++11 is the modern minimum. This site targets C++17; some later content exists for newer compilers.

Which standard:
- Learning / personal projects: the latest finalized standard your compiler supports.
- Professional work: often one or two versions behind the newest finalized standard (tooling maturity, defects, cross-platform support).

Experimental / preview support for an unfinalized standard can be incomplete or buggy.

The standards document is the formal spec for compiler writers, not a textbook. Approved copies are not free; late drafts are online.

A program that “should compile” but does not is often either the wrong (too old) standard selected, or incomplete compiler support for a new feature. cppreference tracks per-compiler feature support.

Export a project template so you do not re-enter these settings every time.
