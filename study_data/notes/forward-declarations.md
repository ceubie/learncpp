1. When addressing compilation errors or warnings in your programs, resolve the first issue listed and then compile again.

2. It is worth noting that function declarations do not need to specify the names of the parameters (as they are not considered to be part of the function declaration). In the above code, you can also forward declare your function like this: 
`int add(int, int); // valid function declaration`

Best practice is to keep the parameter names in your function declarations.

3. In C++, all definitions are declarations. Therefore int x; is both a definition and a declaration. Conversely, not all declarations are definitions. Declarations that aren’t definitions are called pure declarations. Types of pure declarations include forward declarations for function, variables, and types.