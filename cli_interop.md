# cli_interop.py: a CLI interoperability test tool

This is a Python CLI application which test interoperability between Vaser C implementation and Python implementation.
It test the following:
- C implementation encode and Python implementation encode give same result
- That result is decoded correctly by both the C and the Python implementations

Its input arguments are the same as the `encode` command of the Python CLI implementation (cli.py), but `encode` is implicit.
In addition, it takes the following option arguments:
- `--c-impl`: path to the C implementation executable (default is `./test-vaser`)

The tool is doing the following:
- Invoke C CLI implementation `encode` command, save output as `c_output`
- Invoke Python CLI implementation `encode` command, save output as `py_output`
- If `c_output` is not equal to `py_output`: display both in an error message and exit with error code
- display `c_output`
- Invoke C CLI implementation `decode` with `c_output`, save output as `c_decoded`
- Invoke Python CLI implementation `decode` with `c_output`, save output as `py_decoded`
- If both are equal to the original input arguments: display `c_decoded` and exit with success
- If `c_decoded` is not equal to the original input arguments: display both in an error message
- If `py_decoded` is not equal to the original input arguments: display both in an error message
- exit with error code

