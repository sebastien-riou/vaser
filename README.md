# vaser
Variable arguments serialization framework.

Sender may use python library or C library, receiver may use python library or C library. The C library is suitable for running baremetal on tiny MCUs.

The main functionality is simple: send efficiently a list of values over a serial link, a buffer in memory or in a file.

Features:
- Streaming: the list can be sent in multiple chunks
- The protocol parameters can be optimized for sending mostly 'small' values or large ones

The main use case is custom RPC protocols.

Stream layout:
- packet header:
    - size of payload, in bytes, using VLQ encoding
- payload:
    - payload header:
        - number of values in this chunk, using VLQ encoding
        - flags, using VLQ encoding:
            - fragment bit: 1 when last value is fragmented, i.e. this chunk contains only part of it
            - last bit: 1 when last value is the last of the whole list
    - size of values: encoded using VLQ
    - values

Alternative stream layout to allow simultaneous encoding and sending:
- use TLV format (Tag, Length, Value), with TL encoded as VLQ
- Tags: (encoded on 2 bits, the 2 LSB of TL)
    - 11 Last in List
    - 10 Last in chunk
    - 01 Fragment (last in chunk, but truncated)
    - 00 Default
- Stream layout is simply a collection of TLV ending with 'Last in List'
