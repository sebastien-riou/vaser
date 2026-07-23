Serialized format
=================

A single chunk is encoded as a very small self-delimiting wire format that
consists of a header followed by a payload.

Header
------

The first field is the payload size in bytes, encoded with a variable-length
quantity (VLQ) scheme. The size is followed by the payload itself.

Payload
-------

The payload contains:

1. the number of values in the chunk, encoded as VLQ
2. a flags field, also encoded as VLQ
3. one VLQ-encoded value per argument

Flags
-----

The flags field uses the following bits:

- bit 0: ``fragment`` flag
- bit 1: ``last`` flag

The encoder rejects an invalid combination where both bits are set. In other
words, a chunk cannot be both fragmented and final at the same time.

Encoding notes
--------------

- Every field is encoded in groups of 7 bits, with a continuation bit used to
  indicate whether more groups follow.
- The format is designed for compact transmission over serial links and other
  byte-oriented channels.
- The decoder can reconstruct the original integer values and the chunk flags
  from the serialized bytes.

Example
-------

A chunk containing the values ``4`` and ``13`` can be serialized and later
reconstructed by calling :meth:`vaser.Vaser.add` and :meth:`vaser.Vaser.finalize`,
or through the CLI with the ``encode`` and ``decode`` commands.
