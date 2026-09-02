1. The preprocessor does not actually modify the original code files in any way -- rather, all changes made by the preprocessor happen either temporarily in-memory or using temporary files.

2. Historically, the preprocessor was a separate program from the compiler, but in modern compilers, the preprocessor may be built right into the compiler itself.

3. Preprocessor directives (often just called directives) are instructions that start with a # symbol and end with a newline (NOT a semicolon). These directives tell the preprocessor to perform certain text manipulation tasks. Note that the preprocessor does not understand C++ syntax -- instead, the directives have their own syntax (which in some cases resembles C++ syntax, and in other cases, not so much).

4. The final output of the preprocessor contains no directives -- only the output of the processed directive is passed to the compiler.

5. Each translation unit typically consists of a single code (.cpp) file and all header files it #includes (applied recursively, since header files can #include other header files).

6. Macro names should be written in all uppercase letters, with words separated by underscores. 

7. Once the preprocessor has finished, all defined identifiers from that file are discarded. This means that directives are only valid from the point of definition to the end of the file in which they are defined. Directives defined in one file do not have any impact on other files (unless they are #included into another file). For example: