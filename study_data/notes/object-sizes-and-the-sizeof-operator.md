For maximum portability, you shouldn’t assume that objects are larger than the specified minimum size.

Alternatively, if you want to assume that a type has some non-minimum size (e.g. that an int is at least 4 bytes), you can use static_assert to have the compiler fail a build if it is compiled on an architecture where this assumption is not true. We cover how to do this in lesson 9.6 -- Assert and static_assert.

sizeof does not include dynamically allocated memory used by an object

CPUs are often optimized to process data of a certain size (e.g. 32 bits), and types that match that size may be processed quicker. On such a machine, a 32-bit int could be faster than a 16-bit short or an 8-bit char.