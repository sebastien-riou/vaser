# vaser
Variable arguments serialization protocol.

Sender may use python library or C library, receiver may use python library or C library. The C library is suitable for running baremetal on tiny MCUs.

The main functionality is simple: send efficiently a list of values over a serial link, a buffer in memory or in a file.

Features:
- Support 0 bytes values
- Streaming: the list can be sent in multiple chunks
- Interface bridge friendly: the implementation of 'dumb' bridge is easy (state-less)

The main use case is custom RPC protocols.

This repo provides the following test programs:
- `./test-vaser`: test program for the C implementation
- `python -m vaser.cli`: test program for the Python implementation 
- `python -m test.cli_interop`: program to test interoperability between the C and the python implementation

## How to test Python implementation
`pipenv run pytest`

## How to build C test program 
`./buildit`

## How to test C implementation and interoperability with Python
`pipenv run ./test-cli-interop`

## Details

Concept: 
- Use TLV format (Tag, Length, Value), with TL encoded as VLQ
- A chunk consist of one or more TLV. Last tag of the chunk is either 'Last in list' or 'Last in chunk' or 'Fragment'.
- A list consist of one or more chunks. Last tag of the last chunk is 'Last in list'.

Tags encoding: (encoded on 2 bits, the 2 LSB of TL)
    - 11 Last in list
    - 10 Last in chunk
    - 01 Fragment (last in chunk, but truncated)
    - 00 Default