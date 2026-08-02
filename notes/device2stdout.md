# device2stdout

this is a python CLI application than copy each byte it gets on its input serial device to `stdout`.
The path to the input serial device is specified via the 1st CLI argument. 
Optional arguments:
- `--baud`: specify the baudrate to use for the serial device
- `--pts`: the application is creating a pts device and create a soft link to the pts at the location specified for the input device. 

When the application terminates, if `--pts` was used, it delete the soft link it created.

