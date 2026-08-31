Assignment happens *after* a variable already exists. Initialization happens *when* it is created.

Assignment
`=` is the assignment operator. By default it copy-assigns: the right-hand value is copied into the left-hand variable, overwriting whatever was there. A normal variable holds one value at a time.

```
int width;   // defined, not yet given a value here
width = 5;   // assignment
width = 7;   // assignment again — 5 is gone
```

Do not confuse `=` (assign) with `==` (test equality).

The downside of assignment-only: two statements to get a starting value. Combine them with initialization instead.

Initialization
Providing an initial value at the point of definition. The syntax is an **initializer**; informally the value itself is also called that. Think “initial-ization.”

Five common forms:

| Form | Syntax | Name |
|---|---|---|
| no initializer | `int a;` | default-initialization |
| `=` then a value | `int b = 5;` | copy-initialization |
| value in `()` | `int c(6);` | direct-initialization |
| value in `{}` | `int d{ 7 };` | direct-list-initialization (preferred) |
| empty `{}` | `int e{};` | value-initialization (preferred when you do not care about the starting value) |

As of C++17, copy, direct, and direct-list initialization behave the same in most cases. The important difference for now is narrowing (below).

Default-initialization
No initializer. For `int` and most built-in types this often does **no** initialization. The variable holds an indeterminate (“garbage”) value. Prefer not to do this. Details in 1.6.

Copy-initialization
`int width = 5;` Inherited from C. Copies the right-hand value into the new variable. Used to be less efficient for some class types; C++17 fixed most of that. Still common in older / C-style code. Also used behind the scenes when passing/returning by value.

Direct-initialization
`int width(5);` Parentheses. Added so class types could initialize more efficiently. Easy to confuse with a function call. Largely replaced by list-initialization, but still used in a few cases (including explicit casts like `static_cast`).

List-initialization (brace / uniform initialization)
The modern form. Curly braces mean we are initializing.

- Direct-list-initialization: `int width{ 5 };` — preferred when you have a real initial value.
- Copy-list-initialization: `int height = { 6 };` — rarely used.

Reasons it won:
- One syntax that works in almost every situation.
- Unambiguous: `{}` means initialize. `=` could be assignment; `()` could be a function.
- Can take a *list* of values later (vectors, etc.).
- **Disallows narrowing conversions.** The compiler must diagnose them.

Narrowing
A conversion that loses information, e.g. `4.5` into an `int` (fraction dropped → `4`).

```
int w1{ 4.5 };   // error (or required diagnostic): list-init refuses to narrow
int w2 = 4.5;    // compiles: copy-init silently becomes 4
int w3(4.5);     // compiles: direct-init silently becomes 4
w1 = 4.5;        // assignment still allows narrowing even if w1 was list-init
```

That last point: the narrowing ban applies to list-initialization, not to later assignments.

Value-initialization and zero-initialization
Empty braces: `int width{};`

This is value-initialization. For `int` and most built-in types it zero-initializes (sets the value to `0`, or the closest thing to zero for that type). For class types it may use a predefined default, which might not be zero.

`{ 0 }` vs `{}`
- `int x{ 0 };` when you are actually going to *use* that 0.
- `int x{};` when the value is temporary and will be replaced immediately (e.g. `std::cin >> x;`). An explicit 0 would be meaningless.

Best practices
- Prefer direct-list-initialization (`int x{ 5 };`) or value-initialization (`int x{};`).
- Initialize every variable when you create it. Only skip that on purpose.

Instantiation
Created (allocated) *and* initialized, including default-initialization. The object is an instance. You will hear this most with class types.

Multiple variables on one line
Legal but easy to get wrong. Each variable only takes *its own* initializer:

```
int a, b = 5;      // a is NOT 5 — a is default-initialized (garbage for int)
int a = 5, b = 5;  // both 5
```

Still better: one variable per line.

Unused variables
An initialized-but-unused variable is a warning (and an error if you treat warnings as errors). Fix by removing it, or actually using it.

C++17 `[[maybe_unused]]` tells the compiler you are okay with that variable not being used (e.g. a shared list of constants where this program only needs some of them). Do not sprinkle it on leftovers you should have deleted.
