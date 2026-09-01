1. Some operating systems do not output a newline before showing the command prompt after running an executable from the command line. 
If a program does not end with a cursor on a new line, the command prompt may appear appended to the prior line out output.
Best practice is to program a newline whenever a line of output is complete

2. The opposite of buffered output is unbuffered output. With unbuffered output, each individual output request is sent directly to the output device.

Writing data to a buffer is typically fast, whereas transferring a batch of data to an output device is comparatively slow. Buffering can significantly increase performance by batching multiple output requests together to minimize the number of times output has to be sent to the output device.

3. Each line of input data in the input buffer is terminated by a '\n' character.

4. "Run #2: When std::cin >> x is encountered, the program will wait for input. Enter 4 5. The input 4 5\n goes into the input buffer, but only the 4 is extracted to variable x (extraction stops at the space).

When std::cin >> y is encountered, the program will not wait for input. Instead, the 5 that is still in the input buffer is extracted to variable y. The program then prints You entered 4 and 5.

Note that in run 2, the program didn’t wait for the user to enter additional input when extracting to variable y because there was already prior input in the input buffer that could be used."

5. If no characters could be extracted, extraction has failed. The object being extracted to is copy-assigned the value 0 (as of C++11), and any future extractions will immediately fail (until std::cin is cleared).
Any non-extracted characters (including newlines) remain available for the next extraction attempt.