The compiler is only required to evaluate constant expressions at compile-time in contexts that require a constant expression. It may or may not do so in other cases.

The likelihood that an expression is fully evaluated at compile-time can be categorized as follows:

Never: A non-constant expression where the compiler is not able to determine all values at compile-time.
Possibly: A non-constant expression where the compiler is able to determine all values at compile-time (optimized under the as-if rule).
Likely: A constant expression used in a context that does not require a constant expression.
Always: A constant expression used in a context that requires a constant expression.