1. Note that conditional compilation directives are also not required using this method, as most loggers have a method to reduce/eliminate writing output to the log. This makes the code a lot easier to read, as the conditional compilation lines add a lot of clutter. With plog, logging can be temporarily disabled by changing the init statement to the following:

 plog::init(plog::none , "Logfile.txt"); // plog::none eliminates writing of most messages, essentially turning logging off

2. In larger or performance-sensitive projects, faster and more feature-rich loggers may be preferred, such as spdlog.