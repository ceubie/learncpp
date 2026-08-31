1. Some operating systems do not output a newline before showing the command prompt after running an executable from the command line. 
If a program does not end with a cursor on a new line, the command prompt may appear appended to the prior line out output.
Best practice is to program a newline whenever a line of output is complete

2. The opposite of buffered output is unbuffered output. With unbuffered output, each individual output request is sent directly to the output device.

Writing data to a buffer is typically fast, whereas transferring a batch of data to an output device is comparatively slow. Buffering can significantly increase performance by batching multiple output requests together to minimize the number of times output has to be sent to the output device.