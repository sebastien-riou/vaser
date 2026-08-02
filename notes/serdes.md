# SERDES CLI applications

## serialize.py
`serialize.py` is encoding its argument and transmit it over a serial device or `stdout`.
Its input arguments are the same as the `encode` command of the Python CLI implementation (cli.py), but `encode` is implicit.
In addition, it takes the following optional argument:
- `--device`: path to a serial device. output will be sent to it rather than on `stdout`.

## deserialize.py
`deserialize.py` is decoding a byte stream from a serial device or `stdin`. It prints the decoded arguments on `stdout`.
Its input arguments are:
- `--granularity`: same as the Python CLI implementation (cli.py)
- `--device`: path to a serial device. input will be read from it rather than from `stdin`.

