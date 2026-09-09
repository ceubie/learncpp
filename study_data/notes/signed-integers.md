The C++20 standard makes this blanket statement: “If during the evaluation of an expression, the result is not mathematically defined or not in the range of representable values for its type, the behavior is undefined”. Colloquially, this is called overflow.

In general, overflow results in information being lost, which is almost never desirable. If there is any suspicion that an object might need to store a value that falls outside its range, use a type with a bigger range!

Be careful when using integer division, as you will lose any fractional parts of the quotient. However, if it’s what you want, integer division is safe to use, as the results are predictable.