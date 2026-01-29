# Layer Image Packing Logic Examples
## Analysis of pack_v3.py lines 759-798

This document provides real examples from the unpacked watchfaces showing each case in the layer packing logic.

---

## Case 1: `drawType in (10, 15, 21)` - Rotation/Pointer Layers

**Purpose**: Clock hands (hour, minute, second) or rotating pointers with offset coordinates.

**Data Structure**: `[x_offset, y_offset, "image_name.png"]`

**Packing Logic**:
```python
if layer['drawType'] in (10, 15, 21):
    clock_layer_data += struct.pack('>i', img[0])      # x offset
    clock_layer_data += struct.pack('>i', img[1])      # y offset
    # Handle z-ordered or regular image
    clock_layer_data += struct.pack('>i', img_objs[img[2]][0])  # image address
    clock_layer_data += struct.pack('>i', img_objs[img[2]][1])  # image length
```

### Example 1A: drawType=21 (Hour Hand with z_ prefix)
**Source**: `J:\Smart_Watch\DT_Watch_11_Pro\tools\from_vendor\tool_gen_clock\tool_gen_clock\tool_gen_clock\config.json`

```json
{
  "name": "6. 24小时 时针",
  "drawType": 21,
  "dataType": 10,
  "alignType": 0,
  "x": 0,
  "y": 0,
  "num": 18,
  "imgArr": [
    [20, 203, "z_clock_4355_hour_24_0.png"],
    [21, 203, "z_clock_4355_hour_24_1.png"],
    [21, 201, "z_clock_4355_hour_24_2.png"],
    [21, 198, "z_clock_4355_hour_24_3.png"]
  ]
}
```
- **Explanation**: 24-hour clock hand with 18 rotation frames
- Each array: `[x_pivot, y_pivot, z_ordered_image]`
- The `z_` prefix means it's stored in the z-image section with special addressing

### Example 1B: drawType=21 (Minute Hand - regular images)
**Source**: Same config.json

```json
{
  "name": "10. 分针",
  "drawType": 21,
  "dataType": 12,
  "alignType": 0,
  "x": 0,
  "y": 0,
  "num": 15,
  "imgArr": [
    [25, 208, "clock_50091_minute_00.png"],
    [28, 207, "clock_50091_minute_01.png"],
    [31, 204, "clock_50091_minute_02.png"]
  ]
}
```

### Example 1C: drawType=10 (Second Hand)
**Source**: Same config.json

```json
{
  "name": "11. 秒针",
  "drawType": 10,
  "dataType": 13,
  "alignType": 0,
  "x": 0,
  "y": 0,
  "num": 15,
  "imgArr": [
    [9, 198, "clock_50091_second_00.png"],
    [10, 198, "clock_50091_second_01.png"],
    [11, 195, "clock_50091_second_02.png"]
  ]
}
```

### Example 1D: drawType=15 (Rotating Hour Display)
**Source**: `J:\Smart_Watch\DT_Watch_11_Pro\watchfaces\unpacked\Clock55005_res_unpacked\chunks_decoded\config.json`

```json
{
  "drawType": 15,
  "dataType": 11,
  "alignType": 1,
  "x": 2,
  "y": 2,
  "num": 1,
  "imgArr": [
    [233, 233, "layer_011_chunk_000.png"]
  ]
}
```

---

## Case 2: `drawType == 55 and idx == 2` - String Encoding

**Purpose**: Encode screen/function names as 30-byte strings (e.g., jump to specific screens).

**Data Structure**: `[width, height, "ScreenName", "icon.png"]`

**Packing Logic**:
```python
elif layer['drawType'] == 55 and idx == 2:
    clock_layer_data += struct.pack('30s', img.encode())  # Fixed 30-byte string
```

### Example 2: Screen Jump Button
**Source**: `J:\Smart_Watch\DT_Watch_11_Pro\watchfaces\unpacked\Clock4651_res_unpacked\chunks_decoded\config.json`

```json
{
  "drawType": 55,
  "dataType": 0,
  "alignType": 0,
  "x": 51,
  "y": 405,
  "num": 4,
  "imgArr": [
    42,                      // idx=0: width (integer)
    42,                      // idx=1: height (integer)
    "AlarmNewScreen",        // idx=2: screen name (encoded as 30 bytes)
    "layer_010_chunk_000.png" // idx=3: button icon image
  ]
}
```
- **Explanation**: A button at position (51, 405) sized 42x42 that jumps to "AlarmNewScreen"
- Only the string at index 2 gets special 30-byte encoding
- Other indices are handled by other cases

---

## Case 3: `dataType in (64, 65, 66, 67) and idx in (10, 11)` - Special Date Data

**Purpose**: Time digit display for top-left hour, top-right hour, bottom-left minute, bottom-right minute.

**Data Types**:
- **64**: Top-left time digit (e.g., tens place of hour)
- **65**: Top-right time digit (e.g., ones place of hour)
- **66**: Bottom-left time digit (e.g., tens place of minute)
- **67**: Bottom-right time digit (e.g., ones place of minute)

**Packing Logic**:
```python
elif layer['dataType'] in (64, 65, 66, 67) and idx in (10, 11):
    clock_layer_data += struct.pack('>i', img)  # Pack as integer
```

### Example 3: Four-Corner Time Display
**Source**: `J:\Smart_Watch\DT_Watch_11_Pro\watchfaces\unpacked\Clock4801_res_unpacked\chunks_decoded\config.json`

```json
{
  "drawType": 1,
  "dataType": 64,
  "alignType": 0,
  "x": 0,
  "y": 0,
  "num": 10,
  "imgArr": [
    "layer_001_chunk_000.png",  // idx=0: digit 0
    "layer_001_chunk_001.png",  // idx=1: digit 1
    "layer_001_chunk_002.png",  // idx=2: digit 2
    ...
    "layer_001_chunk_009.png"   // idx=9: digit 9
    // idx 10, 11 would be integers if present
  ]
}
```

```json
{
  "drawType": 1,
  "dataType": 65,
  "alignType": 0,
  "x": 210,
  "y": 0,
  "num": 10,
  "imgArr": [
    "layer_002_chunk_000.png",
    // ... digits 0-9
  ]
}
```

```json
{
  "drawType": 1,
  "dataType": 66,
  "alignType": 0,
  "x": 6,
  "y": 224,
  "num": 10,
  "imgArr": [
    "layer_003_chunk_000.png",
    // ... digits 0-9
  ]
}
```

```json
{
  "drawType": 1,
  "dataType": 67,
  "alignType": 0,
  "x": 220,
  "y": 224,
  "num": 10,
  "imgArr": [
    "layer_004_chunk_000.png",
    // ... digits 0-9
  ]
}
```

**Explanation**: 
- Creates a 4-corner digital time display
- Position (0, 0): Hour tens
- Position (210, 0): Hour ones
- Position (6, 224): Minute tens
- Position (220, 224): Minute ones
- Special integers at indices 10-11 could control formatting

---

## Case 4: `drawType == 8 and idx in (0, 1, 2)` - First Three Elements Are Integers

**Purpose**: Draw type 8 has special configuration where first 3 elements are integer parameters.

**Packing Logic**:
```python
elif layer['drawType'] == 8 and idx in (0, 1, 2):
    clock_layer_data += struct.pack('>i', img)  # Pack as integer
```

### Example 4: Configuration Parameters
**Note**: No examples found in current unpacked watchfaces. This is a rare case.

**Hypothetical Structure**:
```json
{
  "drawType": 8,
  "dataType": X,
  "alignType": 0,
  "x": 100,
  "y": 100,
  "num": 5,
  "imgArr": [
    255,           // idx=0: parameter 1 (integer)
    128,           // idx=1: parameter 2 (integer)
    64,            // idx=2: parameter 3 (integer)
    "image1.png",  // idx=3: handled by other cases
    "image2.png"   // idx=4: handled by other cases
  ]
}
```

---

## Case 5: `isinstance(img, int)` - Generic Integer Values

**Purpose**: Any integer value that doesn't match previous special cases.

**Packing Logic**:
```python
elif isinstance(img, int):
    clock_layer_data += struct.pack('>i', img)  # Pack as integer
```

### Example 5A: drawType=55 (width/height parameters)
**Source**: Clock4651 (shown in Case 2)

```json
{
  "drawType": 55,
  "imgArr": [
    42,    // idx=0: integer (width) - handled by this case
    42,    // idx=1: integer (height) - handled by this case
    "AlarmNewScreen",        // idx=2: string - handled by Case 2
    "layer_010_chunk_000.png" // idx=3: image - other case
  ]
}
```

### Example 5B: Other integer parameters
Any layer configuration with integer values in imgArr will use this case for those integers.

---

## Case 6: `img.startswith('z_')` - Z-Order Images

**Purpose**: Images with special layering/depth (z-order), stored in separate memory section.

**Packing Logic**:
```python
elif img.startswith('z_'):
    clock_layer_data += struct.pack('>i', clock_z_img_start + img_objs[img][0])
    clock_layer_data += struct.pack('>i', img_objs[img][1])
```

### Example 6: Background Images with Z-Order
**Source**: `J:\Smart_Watch\DT_Watch_11_Pro\tools\from_vendor\tool_gen_clock\tool_gen_clock\tool_gen_clock\config.json`

```json
{
  "name": "3. 卡路里 背景",
  "drawType": 20,
  "dataType": 42,
  "alignType": 0,
  "x": 276,
  "y": 72,
  "num": 11,
  "imgArr": [
    "z_clock_156_kcal_bg_00.png",
    "z_clock_156_kcal_bg_01.png",
    "z_clock_156_kcal_bg_02.png",
    "z_clock_156_kcal_bg_03.png",
    "z_clock_156_kcal_bg_04.png",
    "z_clock_156_kcal_bg_05.png",
    "z_clock_156_kcal_bg_06.png",
    "z_clock_156_kcal_bg_07.png",
    "z_clock_156_kcal_bg_08.png",
    "z_clock_156_kcal_bg_09.png",
    "z_clock_156_kcal_bg_10.png"
  ]
}
```

**Explanation**:
- These images are stored in the z-image section (clock_z_img_data)
- Address calculation: `clock_z_img_start + img_objs[img][0]`
- Used for images that need to overlay or layer in specific ways

---

## Case 7: Default - Regular Image References

**Purpose**: Standard image references without special handling.

**Packing Logic**:
```python
else:
    clock_layer_data += struct.pack('>i', img_objs[img][0])  # image address
    clock_layer_data += struct.pack('>i', img_objs[img][1])  # image length
```

### Example 7A: Background Layer
**Source**: `J:\Smart_Watch\DT_Watch_11_Pro\watchfaces\unpacked\Clock3115_res_unpacked\chunks_decoded\config.json`

```json
{
  "drawType": 0,
  "dataType": 0,
  "alignType": 0,
  "x": 0,
  "y": 0,
  "num": 1,
  "imgArr": [
    "layer_000_chunk_000.png"
  ]
}
```

### Example 7B: Animation Frames
**Source**: Same file

```json
{
  "drawType": 20,
  "dataType": 21,
  "alignType": 0,
  "x": 44,
  "y": 94,
  "num": 12,
  "imgArr": [
    "layer_001_chunk_000.png",
    "layer_001_chunk_001.png",
    "layer_001_chunk_002.png",
    "layer_001_chunk_003.png",
    "layer_001_chunk_004.png",
    "layer_001_chunk_005.png",
    "layer_001_chunk_006.png",
    "layer_001_chunk_007.png",
    "layer_001_chunk_008.png",
    "layer_001_chunk_009.png",
    "layer_001_chunk_010.png",
    "layer_001_chunk_011.png"
  ]
}
```

**Explanation**: 
- Standard images stored in regular image section (clock_img_data)
- Each image gets address and length packed as two integers

---

## Additional Context: Special dataType Values

Based on the code and examples:

### Animation/Update Intervals
```python
if layer['dataType'] in {130, 59, 52}:
    clock_layer_data += struct.pack('>i', layer['interval'])
```
- These dataTypes require an interval parameter for animation timing

### Area Numbers
```python
if layer['dataType'] in {112}:
    for _, value in enumerate(layer['area_num']):
        clock_layer_data += struct.pack('>i', value)
```
- dataType 112 requires area_num array

---

## Summary Table

| Case | Condition | Example DataType | Example DrawType | Data Structure | Use Case |
|------|-----------|------------------|------------------|----------------|----------|
| 1 | drawType in (10,15,21) | 10-13 | 10,15,21 | [x,y,img] | Clock hands, pointers |
| 2 | drawType==55, idx==2 | 0 | 55 | string | Screen navigation |
| 3 | dataType in (64-67), idx in (10,11) | 64-67 | 1 | integers | Four-corner time |
| 4 | drawType==8, idx in (0,1,2) | varies | 8 | integers | Special config |
| 5 | isinstance(img, int) | any | any | integer | Generic parameters |
| 6 | img.startswith('z_') | any | any | string | Z-ordered images |
| 7 | default | any | 0,1,20 | string | Regular images |

---

## Binary Packing Summary

All values are packed as **big-endian 32-bit integers** (`'>i'`) except:
- Case 2: 30-byte fixed string (`'30s'`)

Each layer writes:
1. drawType (4 bytes)
2. dataType (4 bytes)
3. [conditional] interval (4 bytes) - if dataType in {130, 59, 52}
4. [conditional] area_num values (4 bytes each) - if dataType == 112
5. alignType (4 bytes)
6. x position (4 bytes)
7. y position (4 bytes)
8. num (count of images) (4 bytes)
9. Image array data (varies by case above)
