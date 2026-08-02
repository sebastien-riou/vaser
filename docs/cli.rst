Command-line interface
======================

The CLI provides two entry points:

- ``encode`` serializes one or more chunks of hexadecimal payloads to bytes
- ``decode`` parses encoded bytes back into payloads and chunk markers

The Python CLI accepts a top-level ``--granularity`` option for padding
and uses markers to delimit chunk boundaries and finalization.

Encoding
--------

Use ``encode`` with payload bytes expressed in hexadecimal. The special
keyword ``null`` encodes an empty payload. Chunk boundary markers are
specified as separate arguments after their payloads:

- ``next`` marks the current payload as the last argument in the current
  chunk and starts a new chunk after it.
- ``fragment`` marks the current payload as a fragmented chunk.
- ``last`` marks the current payload as the final chunk in the list.

If the final payload is not followed by a marker, the CLI finalizes the
current chunk implicitly.

Example:

.. code-block:: console

   pipenv run python -m vaser --granularity 1 encode 010203 next 0405 last

Decoding
--------

Use ``decode`` with one or more hexadecimal-encoded chunks. The decoder
prints decoded payloads in hex, using the same markers to indicate
chunk boundaries and finalization.

Example:

.. code-block:: console

   pipenv run python -m vaser --granularity 1 decode 0e0102030b0405

Options
-------

``--granularity N``
    Top-level option that controls the read/write padding granularity when
    encoding or decoding chunks that are not using the default flag state.
    The default value is ``1``.

