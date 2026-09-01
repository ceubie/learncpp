1. C does allow main() to be called explicitly, so some C++ compilers will allow this for compatibility reasons.

2. The return value from main() is sometimes called a status code (or less commonly, an exit code, or rarely a return code). The status code is used to signal whether your program was successful or not. By convention, a status code of 0 means the program ran normally (meaning the program executed and behaved as expected). Best practice is the main function should return a value of 0 to display a successful run of a program. 

A non-zero status code is often used to indicate some kind of failure (and while this works fine on most operating systems, strictly speaking, it’s not guaranteed to be portable).

The status code is passed back to the operating system. The OS will typically make the status code available to whichever program launched the program returning the status code. This provides a crude mechanism for any program launching another program to determine whether the launched program ran successfully or not.

3. The C++ standard only defines the meaning of 3 status codes: 0, EXIT_SUCCESS, and EXIT_FAILURE. 0 and EXIT_SUCCESS both mean the program executed successfully. EXIT_FAILURE means the program did not execute successfully.

EXIT_SUCCESS and EXIT_FAILURE are preprocessor macros defined in the <cstdlib> header:

#include <cstdlib> // for EXIT_SUCCESS and EXIT_FAILURE
int main()
{
 return EXIT_SUCCESS;
}
If you want to maximize portability, you should only use 0 or EXIT_SUCCESS to indicate a successful termination, or EXIT_FAILURE to indicate an unsuccessful termination.