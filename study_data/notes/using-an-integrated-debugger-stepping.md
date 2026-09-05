1. In a prior lesson, we mentioned that std::cout is buffered, which means there may be a delay between when you ask std::cout to print a value, and when it actually does. Because of this, you may not see the value 5 appear at this point. To ensure that all output from std::cout is output immediately, you can temporarily add the following statement to the top of your main() function:

std::cout << std::unitbuf; // enable automatic flushing for std::cout (for debugging)
For performance reasons, this statement should be removed or commented out after debugging.

If you don’t want to continually add/remove/comment/uncomment the above, you can wrap the statement in a conditional compilation preprocessor directive