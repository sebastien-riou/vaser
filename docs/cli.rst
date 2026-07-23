Command-line interface
======================

The CLI provides two entry points:

- ``encode`` serializes one or more chunks of integer values to bytes
- ``decode`` parses encoded bytes back into values and chunk markers

Usage overview
--------------

Encode a simple chunk:

.. code-block:: console

   python -m vaser encode 4 13 --hex

Encode a chunk and mark it as fragmented:

.. code-block:: console

   python -m vaser encode 4 13 --fragment --hex

Encode a chunk and mark it as the last one:

.. code-block:: console

   python -m vaser encode 4 13 --last --hex

Decode a hexadecimal payload:

.. code-block:: console

   echo 848282848d | python -m vaser decode --hex

Chunk markers
-------------

The CLI accepts special marker words when encoding multiple logical chunks in
one invocation:

- ``fragment`` marks current chunk as fragmented
- ``last`` marks current chunk as the final chunk
- ``next`` close the current chunk and starts a new one

Example:

.. code-block:: console

   python -m vaser encode 4 fragment 13 last --hex

The decoder will emit the corresponding chunk markers in its output.

Options
-------

The command-line interface accepts the following options:

- ``--fragment``: mark the current chunk as fragmented
- ``--last``: mark the current chunk as the final chunk
- ``--hex``: read or write hexadecimal text instead of raw bytes
- ``--output``: write encoded or decoded output to a file
- ``--input``: read encoded bytes from a file during decoding
- ``--hex-in``: decode a hexadecimal string supplied directly as an argument
