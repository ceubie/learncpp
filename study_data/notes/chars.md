```
Input a keyboard character: a b
You entered: a
You entered: b
```
In the above example, we may have expected to extract the space, but because leading whitespace is skipped, we extracted the b character instead.
One simple way to address this is to use the std::cin.get() function to perform the extraction instead, as this function does not ignore leading whitespace:
```
Input a keyboard character: a b
You entered: a
You entered:  
```


| Name | Symbol | Meaning |
|-------|----------|-----------|
| Alert | \a | Makes an alert, such as a beep |
| Backspace | \b | Moves the cursor back one space |
| Formfeed | \f | Moves the cursor to next logical page |
| Newline	| \n | Moves cursor to next line |
| Carriage return | \r | Moves cursor to beginning of line |
| Horizontal tab | \t | Prints a horizontal tab |
| Vertical tab | \v | Prints a vertical tab |
| Single quote | \’ | Prints a single quote |
| Double quote | \” | Prints a double quote |
| Backslash | \\	| Prints a backslash. |
| Question mark | \?	| Prints a question mark. 
No longer relevant. You can use question marks unescaped. |
| Octal number | \(number) | Translates into char represented by octal |
| Hex number | \x(number) | Translates into char represented by hex number |