Programs produce results by manipulating data. Data is any information a computer can move, process, or store. In a running program we usually say “code” for the program itself and “data” for the information it works on.

Value and literal
A value is a single piece of data: a number (`5`, `-6.7`), a character (`'H'`), or text (`"Hello"`).
- Single quotes → character (one symbol).
- Double quotes → text (zero or more characters).
- Numbers are not quoted.

A literal is a value written directly in the source. Literals are read-only. Missing quotes on a character or text value makes the compiler treat it as code, which almost always fails to compile.

Object and variable
RAM is the computer’s main memory. The OS loads the program into RAM and reserves more RAM for values the program creates while it runs.

C++ does not want you to address raw memory boxes. An **object** is a region of storage (RAM or a CPU register) that can hold a value. An object with a name (identifier) is a **variable**. The compiler picks where it lives.

A **definition** (`int x;`) tells the compiler we want a variable of a given name and type. At compile time the compiler records that. At runtime, **allocation** reserves actual storage. The object is created once that storage exists.

Data type
A type says what kind of value the object stores, and it must be known at compile time. It cannot change without recompiling.

`int` is an integer: a number with no fractional part (`4`, `0`, `-12`). `double` is a floating-point type (covered later).

Multiple variables
`int a, b;` is legal (same type only). Do not write `int a, int b;` or mix types in one statement.

Best practice: one variable per statement, on its own line, with a comment about what it is for.
