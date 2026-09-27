Although std::string is required to be null-terminated (as of C++11), the returned length of a std::string does not include the implicit null-terminator character.

If using std::getline() to read strings, use std::cin >> std::ws input manipulator to ignore leading whitespace. This needs to be done for each std::getline() call, as std::ws is not preserved across calls.

Note that instead of asking for the string length as length(name), we say name.length(). The length() function isn’t a normal standalone function -- it’s a special type of function that is nested within std::string called a member function. Because the length() member function is declared inside of std::string, it is sometimes written as std::string::length() in documentation.