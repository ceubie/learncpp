1. Much like a person’s lifetime is defined to be the time between their birth and death, an object’s lifetime is defined to be the time between its creation and destruction. Note that variable creation and destruction happen when the program is running (called runtime), not at compile time. Therefore, lifetime is a runtime property.

2. What happens when an object is destroyed? In most cases, nothing. The destroyed object simply becomes invalid. If the object is a class type object, prior to destruction, a special function called a destructor is invoked. In many cases, the destructor does nothing, in which case no cost is incurred. Any use of an object after it has been destroyed will result in undefined behavior. At some point after destruction, the memory used by the object will be deallocated (freed up for reuse).

3. Scope is a compile-time property, and trying to use an identifier when it is not in scope will result in a compile error.

4. Define your local variables as close to their first use as reasonable.

5. Due to the limitations of older, more primitive compilers, the C language used to require all local variables be defined at the top of the function.

