1. The compiler compiles each file individually. It does not know about the contents of other code files, or remember anything it has seen from previously compiled code files. So even though the compiler may have seen the definition of function add previously (if it compiled add.cpp first), it doesn’t remember.

This limited visibility and short memory is intentional, for a few reasons:

- It allows the source files of a project to be compiled in any order.
- When we change a source file, only that source file needs to be recompiled.
- It reduces the possibility of naming conflicts between identifiers in different files.

2. When an identifier is used in an expression, the identifier must be connected to its definition.

If the compiler has seen neither a forward declaration nor a definition for the identifier in the file being compiled, it will error at the point where the identifier is used.
Otherwise, if a definition exists in the same file, the compiler will connect the use of the identifier to its definition.
Otherwise, if a definition exists in a different file (and is visible to the linker), the linker will connect the use of the identifier to its definition.
Otherwise, the linker will issue an error indicating that it couldn’t find a definition for the identifier.
