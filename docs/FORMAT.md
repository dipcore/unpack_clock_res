# DT Watch 11 Pro `.res` Format (V3) — unpack.py notes

This document describes what the tooling **currently understands** for V3 resources. Any fields not described below are **unknown**
(at least from the code in this repo) and should be treated as implementation-specific.

## File header (common)

All integers are **big-endian** 32-bit unless noted.

```
Offset  Size  Field
0x00    8     Magic ASCII: "Sb@*O2GG" or "II@*24dG"
0x08    4     clock_id (see clock_id encoding below)
0x0C    4     thumb_start
0x10    4     thumb_len
0x14    4     v3: img_start   | v1: thumb_pos (unused; typically equals thumb_start)
0x18    4     img_len
0x1C    4     layer_start
```

### clock_id encoding

The `clock_id` is a 32-bit value encoding resolution, internal flag, and base ID:

```
Bit 31:    Internal/built-in flag (1 = internal, 0 = custom)
Bits 16-23: Resolution prefix
Bits 0-15:  Base watchface ID
```

**Resolution prefixes:**

| Resolution | Prefix (Decimal) | Prefix (Hex) |
|------------|------------------|--------------|
| 454×454    | 983040           | 0x0F0000     |
| 400×400    | 917504           | 0x0E0000     |
| 466×466    | 851968           | 0x0D0000     |
| 390×390    | 786432           | 0x0C0000     |
| 410×502    | 720896           | 0x0B0000     |
| 320×384    | 655360           | 0x0A0000     |
| 320×385    | 655360           | 0x0A0000     |
| 368×448    | 589824           | 0x090000     |
| 390×450    | 524288           | 0x080000     |
| 360×360    | 458752           | 0x070000     |

Example: Clock1555 at 466×466 resolution → `1555 | 0x0D0000 = 0x0D0613` (853523)

### Notes:

Bit 31 is the highest bit in the 32-bit clock_id and serves as a flag to distinguish between:

Internal/built-in (1): Factory watchfaces that come pre-installed with the watch firmware. 

Set by OR'ing with 0x80000000 (binary: 10000000 00000000 00000000 00000000)
Example: 0x8D0613 would be Clock1555 (466×466) marked as internal
Custom (0): User-created or third-party watchfaces that can be installed/deleted by the user.

The bit remains 0 (not set)
Example: 0x0D0613 would be Clock1555 (466×466) as a custom watchface

### V3 layout (pack_v3.py)

- `img_start` is **explicit** in the header at `0x14`.
- `z_img_start = img_start + img_len`.
- Data layout:

```
[thumbnail][images][z_images][layer_data]
```

## Thumbnail block

The thumbnail is stored as an **image chunk** (see “Image chunk format”) or sometimes as a raw
image blob (jpg/png/gif/bmp). The unpacker tries both patterns.

## Image blocks

- **Images** block is a concatenation of chunks (or raw images), referenced by offsets in
  `layer_data`.
- **Z-images** are a separate block located between images and layer_data. These are typically
  referenced with names prefixed `z_` in config files.

## Image chunk format (custom chunk header)

When a chunk has the 16-byte header, unpack.py interprets it as:

```
Byte  Size  Meaning
0     1     img_type
1     1     compressed flag (0/1)
2     3     payload_len (little-endian 24-bit)
5     2     height (12 bits: low 8 in byte5, high 4 in low nibble of byte6)
6     2     width  (12 bits: high nibble of byte6 + byte7)
8     8     unused/reserved (always 0 in observed files)
16    ...   payload bytes (optionally LZ4-compressed)
```

### img_type mapping (as decoded in unpack.py)

| img_type | ext | Notes |
|---------:|-----|-------|
| 3        | gif | Raw GIF payload |
| 9        | jpg | Raw JPEG payload |
| 71       | rgb | rgb8888 (BGRA) |
| 72       | rgb | rgb8565 (RGB565 + alpha byte) |
| 73       | rgb | rgb565 |
| 74       | rgb | rgb1555 (1-bit alpha + RGB) |
| 75       | bmp | index8-like payload (palette + pixels) |

If compressed = 1, payload is LZ4 (block) and must be decompressed to `payload_len` bytes.

## Layer data (`layer_data`)

Layer data is a sequence of layer records. Each layer begins with a fixed header, followed by
`num` entries whose structure depends on `drawType`/`dataType`.

### Layer header

```
int32 drawType
int32 dataType
[optional] int32 interval           (only when dataType in {52, 59, 130})
[optional] int32[] area_num          (only when dataType == 112; count is not stored)
int32 alignType
int32 x
int32 y
int32 num
```

> **area_num count**: not stored in the binary. The unpacker uses `--area-num-count` (default 4)
> and heuristics to infer a plausible count.

### `imgArr` entry decoding (what unpack.py handles)

For each of `num` entries:

1. **drawType == 100 and index < 7**
   - First 7 elements are `int32` parameters (metadata like dimensions, positions, etc.)
   - Remaining elements (index 7+) are image offset/length pairs.

2. **drawType in {10, 15, 21}**
   - Structured entry:

     ```
     int32 param0
     int32 param1
     int32 raw_offset
     int32 length
     ```

   - `raw_offset/length` point into **images** or **z-images**. Offsets are interpreted as:
     - If `0 <= raw_offset <= img_len`: `img` section offset.
     - Else if `z_start <= raw_offset <= layer_start`: `z_img` absolute offset.

3. **drawType in {71, 72, 73, 74, 75, 76} and index in {0, 1}**
   - First two elements are `int32` parameters (typically digit width and spacing).
   - Remaining elements (index 2+) are image offset/length pairs.

4. **drawType == 55 and index == 2**
   - 30-byte string (C-style, null-terminated).

5. **dataType in {64, 65, 66, 67} and index in {10, 11}**
   - Stored as `int32` (non-image parameter slots).

6. **drawType == 8 and index in {0, 1, 2}**
   - Stored as `int32` (non-image parameter slots).

7. **Fallback**
   - The unpacker reads `int32 raw_offset`. If the next 4 bytes plus this offset
     **look like a valid image ref**, it consumes an additional `int32 length` and
     treats the pair as a reference. Otherwise it stores the single `int32` as a
     literal value.

## dataType handling (based on unpack.py)

The format **does not embed semantic descriptions** of `dataType`. The unpacker only knows
how to **parse** certain `dataType` values:

| dataType | Handling in unpack.py | Meaning |
|---------:|------------------------|---------|
| 52       | Reads extra `interval` | Unknown (time/animation?) |
| 59       | Reads extra `interval` | Unknown |
| 130      | Reads extra `interval` | Unknown |
| 112      | Reads extra `area_num` list (count inferred) | Unknown |
| 64,65,66,67 | For indices 10,11 in `imgArr`, read `int32` | Unknown |



## Unpacker outputs

When unpack.py runs successfully, it wr (named by ref ID: `chunk_NNN_*.bin`)
- `chunks_decoded/` — decoded payloads when possible (named by ref ID: `chunk_NNN.*`)
- `chunks_decoded/config.json` — config-like file with decoded chunk names

### Image deduplication

The unpacker implements **reference-level deduplication**:
- Each unique image reference (offset + length pair) gets a single ref ID
- Files are named by ref ID (e.g., `chunk_000.png`, `chunk_001.png`)
- Multiple layers can reference the same image file by ref ID
- Deduplication is based on **binary location** (offset/length), not image content
- If two images have identical pixels but different storage locations, they get separate ref IDs

## Notes / Limitations

- Image names are not stored in the `.res` file. The unpacker generates names using ref IDs (`chunk_NNN.*`).
- For `dataType == 112`, the `area_num` list length is guessed; use `--area-num-count` to tune it.
- Some resources might be stored as raw images without chunk headers; the unpacker will try
  to detect them via magic numbers.
