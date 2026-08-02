Serialized format
=================

Vaser serialize a list of arguments into a sequence of bytes. 
Sometimes it is desirable to break that sequence of bytes into multiple chunks, 
for example if the data is too large for the receiving device or if the first few arguments
can be processed without waiting for the entire list of arguments. 
The serialized format therefore supports chunking and provides markers to indicate the end of a chunk and the end of the list of chunks.

Vaser encodes a chunk as a sequence of argument entries. 
Each entry is encoded using a TLV scheme (Tag-Length-Value). 
The tag and the length are packed into a single integer, called the TL header, which is encoded as a variable-length quantity (VLQ).

The TL header is computed as follows:

- the payload length in bytes, shifted left by 2 bits
- the tag (AKA chunk flags) in the two low bits

The encoded integer is then written as a standard VLQ, where each byte
uses the low 7 bits for data and the high bit as a continuation marker.

The value is simply the raw payload bytes for that argument.


Flags
-----

The two low bits of the TL header indicate the chunk flags:

- ``0``: ``DEFAULT`` — the chunk continues after this argument
- ``1``: ``FRAGMENT`` — this chunk is a fragment
- ``2``: ``LAST_IN_CHUNK`` — this is the final entry in the current chunk
- ``3``: ``LAST_IN_LIST`` — this is the final entry in the current chunk list

Only the final argument in a chunk carries a
non-default flag. All earlier arguments use ``DEFAULT`` so the decoder can
concatenate them into a single chunk.

Example: single argument final chunk
------------------------------------

A chunk containing one argument with payload ``010203`` and final list flag
``LAST_IN_LIST`` is encoded as:

- payload length = 3
- flags = 3
- TL value = ``(3 << 2) | 3 = 0x0f``
- VLQ encoding = ``0f``
- payload bytes = ``010203``

Resulting encoding:

.. code-block:: text

   0f010203

Example: multi-argument chunk terminated with ``LAST_IN_CHUNK``
---------------------------------------------------------------

A chunk with two arguments, ``01`` and ``0203``, where the chunk is not the
final chunk in the list, is encoded as:

- first argument: length = 1, flags = 0, TL = ``(1 << 2) | 0 = 0x04``
- second argument: length = 2, flags = 2, TL = ``(2 << 2) | 2 = 0x0a``

Resulting encoding:

.. code-block:: text

   04010a0203

The decoder reads the first TL and payload, sees ``DEFAULT`` and continues.
It then reads the second TL and payload, sees ``LAST_IN_CHUNK``, and returns
the completed chunk.

Example: fragmented chunk
-------------------------

A single payload ``0102`` marked as ``FRAGMENT`` is encoded as:

- payload length = 2
- flags = 1
- TL value = ``(2 << 2) | 1 = 0x09``
- encoding = ``090102``

.. code-block:: text

   090102

Granularity padding
-------------------

If a chunk is encoded with a granularity greater than 1, the final chunk bytes
are padded with zero bytes so the total chunk length is a multiple of the
granularity.

For example, with granularity ``4`` and a final encoded chunk of length ``6``
bytes, two padding bytes are appended:

.. code-block:: text

   0901020000

The decoder validates that any padding bytes are zero.

Decoder behavior
----------------

The decoder reads entries from the input stream until it encounters an entry
whose flags are not ``DEFAULT``. It returns the concatenated argument values
and the consumed byte length.

When granularity padding is present, the decoder also consumes the trailing
zero bytes up to the configured granularity boundary.

