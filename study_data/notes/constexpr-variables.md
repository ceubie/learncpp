practical rule is: use constexpr for fixed values and calculations you intend to be compile-time constants; use const for runtime values you want to keep unchanged.

Because functions normally execute at runtime, the return value of a function is not constexpr (even when the return expression is a constant expression). This is why five() is not a legal initialization value for constexpr int f.

const variable: its value cannot change.
constexpr variable: its value must be computable at compile time.
constexpr function: it can run at compile time when the call has suitable inputs; it can also run at runtime.