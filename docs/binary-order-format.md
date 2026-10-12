# ChronosMatch — Binary Order Format

## 1. Purpose

This document defines how ChronosMatch stores one order as a fixed-size 64-byte binary record.

The order generator creates orders, the IPC layer transfers them through shared memory, and the matching engine processes them after decoding.

All components must use the same field layout.

## 2. Record Size

* Record size: 64 bytes
* Byte order: Little-endian
* Format string: `<QQqQIB27x`

Each order occupies exactly 64 bytes.

## 3. Binary Field Layout

| Field        | Data type               |     Size | Meaning                        |
| ------------ | ----------------------- | -------: | ------------------------------ |
| order_id     | Unsigned 64-bit integer |  8 bytes | Unique order identifier        |
| sequence     | Unsigned 64-bit integer |  8 bytes | Order sequence number          |
| price        | Signed 64-bit integer   |  8 bytes | Order price in paise           |
| timestamp_ns | Unsigned 64-bit integer |  8 bytes | Order timestamp in nanoseconds |
| quantity     | Unsigned 32-bit integer |  4 bytes | Number of units ordered        |
| side         | Unsigned 8-bit integer  |   1 byte | BUY or SELL                    |
| padding      | Unused bytes            | 27 bytes | Reserved space                 |

Total: 8 + 8 + 8 + 8 + 4 + 1 + 27 = 64 bytes.

## 4. Encoding

Encoding converts an order's fields into a 64-byte record.

The encoder accepts:

`encode(order_id, sequence, price, timestamp_ns, quantity, side)`

It returns a byte sequence of exactly 64 bytes.

## 5. Decoding

Decoding converts a 64-byte record back into its original fields.

The decoder accepts:

`decode(record: bytes)`

It returns the fields in this order:

`(order_id, sequence, price, timestamp_ns, quantity, side)`

The record must be exactly 64 bytes long.

## 6. Validation Rules

A valid order must satisfy these rules:

* `order_id` must be non-negative.
* `sequence` must start at 1 and increase for each new order.
* `price` must be greater than zero.
* `quantity` must be greater than zero.
* `side` must be a valid BUY or SELL value.
* All numeric fields must fit within their declared binary data types.
* The encoder must reject invalid orders rather than silently creating incorrect records.

## 7. Integration Rules

* The order generator must use the same field definitions.
* The IPC producer must transmit the encoded 64-byte record.
* The IPC consumer must decode the record using the same format.
* The matching engine must receive the correct order fields.
* The encoder, decoder, and documentation must remain consistent.

## 8. Important Note

The 64-byte format is the current working format for ChronosMatch. Any change to the field layout or record size must be coordinated across the team.
