Chapter 1 is a broad, shallow first pass so you can write simple programs. Later chapters revisit these topics in depth.

Statement
A statement is an instruction that makes the program perform an action. It is the smallest independent unit of computation in C++, like a sentence in English. Most (not all) statements end in a semicolon. One high-level statement can compile into many machine instructions.

Function
A function is a collection of statements that run in order, top to bottom. Every C++ program must have a function named `main` (all lowercase). When the program runs, the statements inside `main` execute sequentially. The program usually ends after the last statement in `main`.

Writing `main()` (with empty parentheses) is shorthand for “the function named main.” That helps distinguish functions from other named things.

Identifier
The name of a function, object, type, etc. is its identifier.

Characters and text
A character is a single written symbol (`a`, `2`, `$`, `=`). A sequence of characters is text (also called a string). C++ source is plain text.

Hello world, at a glance
- `#include <iostream>` is a preprocessor directive. It pulls in the iostream library so `std::cout` is known.
- `int main()` defines the required `main` function; it returns an `int`.
- `{ }` is the function body.
- `std::cout << "Hello world!";` is the first statement that runs. `cout` = character output.
- `return 0;` sends 0 to the OS, meaning success.

Syntax
Syntax is the set of rules for how tokens and punctuation must be arranged. A syntax error means the program violates those rules. The compiler stops until they are fixed.

Compilers sometimes report the error on the line *after* the real problem (e.g. a missing semicolon). If the marked line looks fine, check the previous line.
