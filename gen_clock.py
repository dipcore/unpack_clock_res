#!/usr/bin/env python3

"""
DT NO.1 smart watch - watch face generator

Pure Python implementation, based on:
https://gist.github.com/dipcore/26a8d0d6508675e5815087398f14499c

Check the `cli_main` function for arguments list
"""

import os, sys, struct, re, logging, logging.handlers, json
from tempfile import TemporaryDirectory
import multiprocessing as mp
from tqdm import tqdm
from PIL import Image
import lz4.block as lz4_block

log_lvl = logging.DEBUG
g_logger = logging.getLogger(__name__)
cpu_core_num = os.cpu_count() or 1

# Logging in the same folder
ROOT = os.path.abspath(os.path.join(os.getcwd()))
g_log_path = os.path.join(ROOT, 'log', 'runtime.log')

g_clock_id_prefix_dict = {
  '454_454': 983040,
  '400_400': 917504,
  '466_466': 851968,
  '390_390': 786432,
  '410_502': 720896,
  '320_384': 655360,
  '320_385': 655360,
  '368_448': 589824,
  '390_450': 524288,
  '360_360': 458752}


def logger_config():
    global g_logger
    g_logger.setLevel(log_lvl)
    if os.path.isfile(g_log_path):
        os.remove(g_log_path)
    if not os.path.isdir(os.path.dirname(g_log_path)):
        os.makedirs(os.path.dirname(g_log_path))
    max_bytes = 10485760
    file_handler = logging.handlers.RotatingFileHandler(g_log_path, maxBytes=max_bytes, backupCount=1)
    file_handler.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(asctime)s L:%(lineno)d %(levelname)s] %(message)s')
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    g_logger.addHandler(file_handler)
    g_logger.addHandler(stream_handler)


def get_filename_list(path):
    """
    Recursively collect all file names under a directory.

    :param path: directory path
    :return: list of file names (lowercased)
    """
    my_list = []
    for filename in os.listdir(path):
        filePath = os.path.join(path, filename)
        if os.path.isdir(filePath):
            my_list += get_filename_list(filePath)
        else:
            my_list.append(filename.lower())
    else:
        return my_list


def check_clock(clock_path):
    """
    Validate a watchface directory and its config, counting missing assets.
    :param clock_path: watchface directory
    :return: True if OK, False otherwise
    """
    if not os.path.isdir(clock_path):
        g_logger.info('Directory does not exist! [%s] ' % clock_path)
        return False

    clock_name = os.path.basename(clock_path)

    config_path = os.path.join(clock_path, 'config.json')
    if not os.path.exists(config_path):
        g_logger.info('Config file missing! [%s] ' % config_path)
        return False

    try:
        with open(config_path, 'r', encoding='utf-8') as config_fd:
            config = json.load(config_fd)
    except Exception as e:
        g_logger.info('Config file read error! [%s] %s' % (clock_name, e))
        return False

    my_list = get_filename_list(clock_path)
    config_img_list = []
    err_count = 0

    for item in config:
        if len(item['imgArr']) != item['num']:
            if item['name']:
                g_logger.info('Watchface[%s]: [image count mismatch]: %s' % (clock_name, item['name']))
            else:
                g_logger.info('Watchface[%s]: [image count mismatch]' % clock_name)
            err_count += 1

        for idx, img in enumerate(item['imgArr']):
            if isinstance(img, list):
                img[-1] = img[-1].lower()
                if img[-1] not in my_list:
                    g_logger.info('Watchface[%s]: [image missing] %s' % (clock_name, img[-1]))
                    err_count += 1
                elif img[-1] not in config_img_list:
                    config_img_list.append(img[-1])
            elif isinstance(img, int):
                continue
            else:
                img = img.lower()
                if item['drawType'] == 55 and idx == 2:
                    continue
                if img not in my_list:
                    g_logger.info('Watchface[%s]: [image missing] %s' % (clock_name, img))
                    err_count += 1
                elif img not in config_img_list:
                    config_img_list.append(img)

    if len(my_list) - 2 != len(config_img_list):
        g_logger.info('Watchface[%s]: total image files: %d, images in config: %d' %
                      (clock_name, len(my_list) - 2, len(config_img_list)))

    if err_count:
        return False
    return True


def get_files(src_path, *ext_list):
    """
    Recursively collect files with given extensions (case-insensitive).
    :param src_path: directory path
    :param ext_list: extensions to include
    :return: list of matching files
    """
    if not (os.path.exists(src_path) and os.path.isdir(src_path)):
        g_logger.info('[%s] is not a directory or does not exist' % src_path)
        return
    ext_list = [ext.lower() for ext in ext_list]
    file_list = []
    for dirpath, dirnames, filenames in os.walk(src_path):
        for file_name in filenames:
            extension = os.path.splitext(file_name)[1].strip('.')
            if extension.lower() in ext_list:
                file_list.append(os.path.join(dirpath, file_name))
        else:
            return file_list


def process_convert_png_2_bmp(file_path: str, tmp_path: str):
    """Pure-Python replacement for ImageMagick `convert.exe` usage.

    Creates a BMP at `<tmp_path/file_name>.bmp`, or a 32-bit BMP with alpha at `<tmp_path/file_name>.BMPA`.
    """
    img = Image.open(file_path)
    file_name = os.path.join(tmp_path, os.path.basename(file_path))

    if img.mode in ("RGBA", "LA") or ("transparency" in img.info):
        img = img.convert("RGBA")
        file_name += ".BMPA"
    else:
        img = img.convert("RGB")
        file_name += ".bmp"

    img.save(file_name, format="BMP")


def convert_png_2_bmpa(src_path: str, tmp_path: str):
    # Convert PNG assets to intermediate bmp/BMPA files (pure Python).
    file_list = get_files(src_path, 'png')
    if not file_list:
        return

    for png_path in file_list:
        try:
            process_convert_png_2_bmp(png_path, tmp_path)
        except Exception as e:
            g_logger.error("PNG convert failed [%s]: %s", png_path, e)


def bmp_2_rgb(file_path):
    """Convert BMP/BMPA intermediates to the device's RGB chunk format.

    This is a corrected, deterministic implementation. The previous port accidentally
    nested all non-565 formats under `if rgb_format == 565`, which caused an infinite
    loop for the common 32-bit BMPA path (rgb8565 / rgb1555 / rgb8888).

    Output file: `<file_path>.RGB` with a 16-byte chunk header followed by pixel payload.
    """
    with open(file_path, 'rb') as f:
        in_data = f.read()

    if len(in_data) < 54 or in_data[0:2] != b'BM':
        g_logger.error('Not a BMP file! [%s]', file_path)
        return

    data_start_addr = struct.unpack('<I', in_data[10:14])[0]
    bmp_w = struct.unpack('<I', in_data[18:22])[0]
    bmp_h = struct.unpack('<I', in_data[22:26])[0]
    bpp_bits = struct.unpack('<H', in_data[28:30])[0]
    bpp = bpp_bits >> 3
    if bpp not in (2, 3, 4):
        g_logger.error('[%s] Unsupported BMP bpp=%d', file_path, bpp_bits)
        return

    # Decide target format from filename suffix + bpp (mirrors original intent)
    rgb_format = 8565
    img_type = 72
    file_name = os.path.basename(file_path).split('.')[0]
    if file_name.endswith('8888'):
        if bpp != 4:
            g_logger.error('[%s] Convert to rgb8888, bpp(%d) != 4', file_path, bpp)
            return
        rgb_format = 8888
        img_type = 71
    elif file_name.endswith('1555') and bpp == 4:
        rgb_format = 1555
        img_type = 74
    elif file_name.endswith('565') or bpp in (2, 3):
        rgb_format = 565
        img_type = 73
    else:
        if bpp != 4:
            g_logger.error('[%s] Convert to rgb8565, bpp(%d) != 4', file_path, bpp)
            return

    # BMP rows are padded to 4-byte boundaries
    row_stride = ((bmp_w * bpp + 3) // 4) * 4

    # Height in BMP can be negative for top-down. Pillow typically writes positive (bottom-up).
    top_down = False
    if bmp_h & 0x80000000:
        # interpret as signed
        bmp_h = struct.unpack('<i', in_data[22:26])[0]
    if bmp_h < 0:
        top_down = True
        bmp_h = -bmp_h

    # Build payload in top-down order (the original code reversed bottom-up BMPs by prepending rows).
    out_payload = bytearray()

    def pack_row(row_bytes: bytes) -> bytes:
        if rgb_format == 565:
            if bpp == 2:
                return row_bytes[:bmp_w * 2]
            # bpp == 3: BGR -> 565 little-endian
            out = bytearray()
            for x in range(bmp_w):
                b = row_bytes[x*3 + 0]
                g = row_bytes[x*3 + 1]
                r = row_bytes[x*3 + 2]
                tmp_16 = ((r & 248) << 8) | ((g & 252) << 3) | ((b & 248) >> 3)
                out += struct.pack('<H', tmp_16)
            return bytes(out)

        if rgb_format == 1555:
            # bpp == 4 expected: BGRA -> 1555 (alpha bit set when alpha==255)
            out = bytearray()
            for x in range(bmp_w):
                b = row_bytes[x*4 + 0]
                g = row_bytes[x*4 + 1]
                r = row_bytes[x*4 + 2]
                a = row_bytes[x*4 + 3]
                tmp_16 = ((r & 248) << 7) | ((g & 248) << 2) | ((b & 248) >> 3)
                if a == 255:
                    tmp_16 |= 0x8000
                out += struct.pack('<H', tmp_16)
            return bytes(out)

        if rgb_format == 8888:
            # bpp == 4: keep BGRA row
            return row_bytes[:bmp_w * 4]

        # rgb8565: bpp == 4 expected: BGRA -> (565 little-endian + alpha byte)
        out = bytearray()
        for x in range(bmp_w):
            b = row_bytes[x*4 + 0]
            g = row_bytes[x*4 + 1]
            r = row_bytes[x*4 + 2]
            a = row_bytes[x*4 + 3]
            tmp_16 = ((r & 248) << 8) | ((g & 252) << 3) | ((b & 248) >> 3)
            out += struct.pack('<HB', tmp_16, a)
        return bytes(out)

    # Determine row iteration order
    y_range = range(bmp_h) if top_down else range(bmp_h - 1, -1, -1)
    for y in y_range:
        off = data_start_addr + y * row_stride
        row = in_data[off: off + row_stride]
        out_payload += pack_row(row)

    out_data_idx = len(out_payload)
    header = struct.pack(
        'BBBBBBBBBBBBBBBB',
        img_type, 0,
        out_data_idx & 0xFF, (out_data_idx >> 8) & 0xFF, (out_data_idx >> 16) & 0xFF,
        bmp_h & 0xFF,
        ((bmp_h >> 8) & 0x0F) | ((bmp_w & 0x0F) << 4),
        (bmp_w >> 4) & 0xFF,
        0, 0, 0, 0, 0, 0, 0, 0
    )

    out_blob = header + bytes(out_payload)
    with open(file_path + '.RGB', 'wb') as out_fd:
        out_fd.write(out_blob)
    return (len(out_blob), out_blob)


def convert_bmp_2_rgb(tmp_path: str):
    """
    Convert BMPs to RGB.
    :param tmp_path: temporary directory
    :return:
    """
    file_list = get_files(tmp_path, 'bmp', 'BMPA')
    if len(file_list):
        pbar = tqdm(total=(len(file_list)), desc='bmp->rgb')
        process_pool = mp.Pool(cpu_core_num)
        for file_path in file_list:
            process_pool.apply_async(bmp_2_rgb, (file_path,), callback=(lambda *args: pbar.update()
), error_callback=process_err_cb)
        else:
            process_pool.close()
            process_pool.join()
            pbar.close()

    else:
        g_logger.info('No files!')


def compress_rgb(tmp_path: str):
    """Pure-Python replacement for compress_rgb.exe.

    For each *.RGB under tmp_path, LZ4-compress the payload and write a sibling *.COMP file
    with the same 16-byte header but compressed flag set to 1.

    Requires `lz4` (pip install lz4).
    """
    rgb_files = get_files(tmp_path, 'RGB')
    if not rgb_files:
        return

    for rgb_path in rgb_files:
        try:
            with open(rgb_path, "rb") as f:
                blob = f.read()
            if len(blob) < 16:
                continue

            header = bytearray(blob[:16])
            if header[1] == 1:
                continue  # already compressed

            payload_len = header[2] | (header[3] << 8) | (header[4] << 16)
            payload = blob[16:]

            if payload_len <= 0 or payload_len > len(payload):
                payload_len = len(payload)
                header[2] = payload_len & 0xFF
                header[3] = (payload_len >> 8) & 0xFF
                header[4] = (payload_len >> 16) & 0xFF

            comp = lz4_block.compress(payload[:payload_len], mode='high_compression', compression=12, store_size=False)
            header[1] = 1
            out_blob = bytes(header) + comp

            out_path = os.path.splitext(rgb_path)[0] + ".COMP"
            with open(out_path, "wb") as f:
                f.write(out_blob)

        except Exception as e:
            g_logger.error("compress_rgb failed [%s]: %s", rgb_path, e)


def image_pre_build(src_path: str, tmp_path: str, is_compress=True):
    """
    Image pre-processing: convert to needed formats.
    :param src_path: source directory
    :param is_compress: compress output or not
    :return: list of produced files [jpg, comp|rgb]
    """
    convert_png_2_bmpa(src_path, tmp_path)
    convert_bmp_2_rgb(tmp_path)
    file_list = get_files(src_path, 'jpg', 'gif')
    if is_compress:
        compress_rgb(tmp_path)
        file_list += get_files(tmp_path, 'COMP')
    else:
        file_list += get_files(tmp_path, 'RGB')
    return file_list


def gen_clock_res(clock_path, dst_path, clock_id_base, clock_size, *, is_compress=True, idle_magic=False, thumbnail_path_override=None):
    """
    Generate a single _res watchface from a source folder.

    Parameters
    ----------
    clock_path : str
        Source folder containing config.json + layer images.
    dst_path : str
        Output directory for the generated Clock*_res file.
    clock_id_base : int
        Base clock id (50000..65535). This will be OR'ed with the resolution prefix.
    clock_size : str
        Watch face size extracted from the image in the bottom layer
    is_compress : bool
        If True, compress eligible image payloads with LZ4 (default True).
    idle_magic : bool
        If True, use idle magic string (II@*24dG) instead of default (Sb@*O2GG).
    thumbnail_path_override : str|None
        Optional path to thumbnail image to embed (PNG/BMP/BMPA supported as raw bytes).
    """
    if not check_clock(clock_path):
        return False

    clock_id = int(clock_id_base)
    clock_id |= g_clock_id_prefix_dict[clock_size]

    is_idle = bool(idle_magic)
    print('\n====Start generating watchface %d(0x%08X)...' % (clock_id & 0xFFFF, clock_id))

    with TemporaryDirectory() as tmp_path:
        file_list = image_pre_build(clock_path, tmp_path, is_compress)
        pbar = tqdm(total=len(file_list), desc='Generate resources')
        thumbnail_path = ''

        try:
            clock_thumb_data = b''
            clock_thumb_start_addr = 32
            clock_thumb_length = 0

            if thumbnail_path_override:
                thumbnail_path = os.path.abspath(thumbnail_path_override)
                if not os.path.exists(thumbnail_path):
                    raise FileNotFoundError(f'Thumbnail not found: {thumbnail_path}')
                with open(thumbnail_path, 'rb') as tf:
                    clock_thumb_data = tf.read()
                clock_thumb_length = len(clock_thumb_data)

            clock_img_data = b''
            clock_img_length = 0

            clock_z_img_data = b''
            clock_z_img_length = 0

            img_objs = {}

            for file_path in file_list:
                base_name = os.path.basename(file_path)
                img_name = base_name.split('.')[0]
                img_ext = base_name.split('.')[1]
                file_name = '.'.join([img_name, img_ext])
                g_logger.debug('[%s] img_name:%s img_ext:%s', file_name, img_name, img_ext)

                file_size = os.path.getsize(file_path)
                in_data = b''

                if img_ext.lower() == 'jpg':
                    img_jpg = Image.open(file_path)
                    width, height = img_jpg.size
                    in_data = struct.pack(
                        'BBBBBBBBBBBBBBBB',
                        9, 0,
                        file_size & 0xFF, (file_size >> 8) & 0xFF, (file_size >> 16) & 0xFF,
                        height & 0xFF,
                        ((height >> 8) & 0x0F) | ((width & 0x0F) << 4),
                        (width >> 4) & 0xFF,
                        0, 0, 0, 0, 0, 0, 0, 0
                    )
                elif img_ext.lower() == 'gif':
                    img_gif = Image.open(file_path)
                    width, height = img_gif.size
                    file_size = os.path.getsize(file_path)
                    in_data += struct.pack(
                        'BBBBBBBBBBBBBBBB',
                        3, 0,
                        file_size & 0xFF, (file_size >> 8) & 0xFF, (file_size >> 16) & 0xFF,
                        height & 0xFF,
                        ((height >> 8) & 0x0F) | ((width & 0x0F) << 4),
                        (width >> 4) & 0xFF,
                        0, 0, 0, 0, 0, 0, 0, 0
                    )

                with open(file_path, 'rb') as in_f:
                    in_data += in_f.read()

                file_size = len(in_data)

                if (not thumbnail_path_override) and ('thumbnail' in file_name):
                    thumbnail_path = os.path.join(clock_path, file_name)
                    clock_thumb_data = in_data
                    clock_thumb_length = file_size
                elif file_name.startswith('z_'):
                    clock_z_img_data += in_data
                    img_objs[file_name] = [clock_z_img_length, file_size]
                    clock_z_img_length += file_size
                else:
                    clock_img_data += in_data
                    img_objs[file_name] = [clock_img_length, file_size]
                    g_logger.debug('[%s] start_addr:0x%08X length:0x%08X', file_name, clock_img_length, file_size)
                    clock_img_length += file_size

                pbar.update()
        except Exception as e:
            g_logger.error('Error: %s', e)
            pbar.close()
            return False
        finally:
            pbar.close()

    try:
        config_path = os.path.join(clock_path, 'config.json')
        with open(config_path, 'r', encoding='utf-8') as conFd:
            layer_list = json.load(conFd)
    except Exception as e:
        g_logger.error('Failed to read config file [%s]: %s', config_path, e)
        return False

    clock_z_img_start = clock_thumb_start_addr + clock_thumb_length + clock_img_length
    clock_layer_data = b''

    for layer in layer_list:
        clock_layer_data += struct.pack('>i', layer['drawType'])
        clock_layer_data += struct.pack('>i', layer['dataType'])
        if layer['dataType'] in {130, 59, 52}:
            clock_layer_data += struct.pack('>i', layer['interval'])
        if layer['dataType'] in {112}:
            for _, value in enumerate(layer['area_num']):
                clock_layer_data += struct.pack('>i', value)

        clock_layer_data += struct.pack('>i', layer['alignType'])
        clock_layer_data += struct.pack('>i', layer['x'])
        clock_layer_data += struct.pack('>i', layer['y'])
        clock_layer_data += struct.pack('>i', layer['num'])

        for idx, img in enumerate(layer['imgArr']):
            if layer['drawType'] in (10, 15, 21):
                clock_layer_data += struct.pack('>i', img[0])
                clock_layer_data += struct.pack('>i', img[1])
                if img[2].startswith('z_'):
                    clock_layer_data += struct.pack('>i', clock_z_img_start + img_objs[img[2]][0])
                    g_logger.debug('[%s] start_addr:0x%08X length:0x%08X', img[2], clock_z_img_start + img_objs[img[2]][0], img_objs[img[2]][1])
                else:
                    clock_layer_data += struct.pack('>i', img_objs[img[2]][0])
                clock_layer_data += struct.pack('>i', img_objs[img[2]][1])
            elif layer['drawType'] == 55 and idx == 2:
                clock_layer_data += struct.pack('30s', img.encode())
            elif layer['dataType'] in (64, 65, 66, 67) and idx in (10, 11):
                clock_layer_data += struct.pack('>i', img)
            elif layer['drawType'] == 8 and idx in (0, 1, 2):
                clock_layer_data += struct.pack('>i', img)
            elif isinstance(img, int):
                clock_layer_data += struct.pack('>i', img)
            elif img.startswith('z_'):
                clock_layer_data += struct.pack('>i', clock_z_img_start + img_objs[img][0])
                g_logger.debug('[%s] start_addr:0x%08X length:0x%08X', img, clock_z_img_start + img_objs[img][0], img_objs[img][1])
                clock_layer_data += struct.pack('>i', img_objs[img][1])
            else:
                clock_layer_data += struct.pack('>i', img_objs[img][0])
                clock_layer_data += struct.pack('>i', img_objs[img][1])

    out_file_name = f'Clock{clock_id_base}_res'
    out_path = os.path.join(dst_path, out_file_name)

    crc_str = 'Sb@*O2GG'
    if is_idle:
        crc_str = 'II@*24dG'

    with open(out_path, 'wb+') as out_f:
        out_f.write(crc_str.encode())
        out_f.write(struct.pack('>I', clock_id))
        out_f.write(struct.pack('>II', clock_thumb_start_addr, clock_thumb_length))

        start_addr = clock_thumb_start_addr + clock_thumb_length
        out_f.write(struct.pack('>II', start_addr, clock_img_length))
        out_f.write(struct.pack('>I', start_addr + clock_img_length + clock_z_img_length))

        out_f.write(clock_thumb_data)
        out_f.write(clock_img_data)
        out_f.write(clock_z_img_data)
        out_f.write(clock_layer_data)

    print('====Watchface done[%s] [%s]\n' % (out_file_name, out_path))
    return (clock_id, out_file_name, out_path, thumbnail_path)


def process_err_cb(err):
    g_logger.error(err)


def _detect_clock_size_from_first_layer(src_dir):
    """
    Detect watchface resolution from the first layer image referenced by config.json.

    Rules:
      - Uses the *first* image in the *first* config entry (first layer).
      - Resolution must be one of the resolutions previously offered in the interactive menu.
    """
    allowed = {
        (466, 466): '466_466',
        (360, 360): '360_360',
        (320, 385): '320_385',
        (368, 448): '368_448',
        (390, 450): '390_450',
    }

    config_path = os.path.join(src_dir, 'config.json')
    if not os.path.exists(config_path):
        raise FileNotFoundError(f'config.json not found in: {src_dir}')

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    if not isinstance(config, list) or not config:
        raise ValueError('config.json must be a non-empty JSON array')

    first = config[0]
    img_arr = first.get('imgArr', [])
    if not img_arr:
        raise ValueError('First config entry has empty imgArr; cannot detect resolution')

    img0 = img_arr[0]
    if isinstance(img0, list):
        img0 = img0[-1]
    if not isinstance(img0, str) or not img0:
        raise ValueError('First layer image reference is invalid')

    img_path = os.path.join(src_dir, img0)
    if not os.path.exists(img_path):
        raise FileNotFoundError(f'First layer image not found: {img_path}')

    with Image.open(img_path) as im:
        size = im.size

    if size not in allowed:
        allowed_str = ', '.join([f'{w}x{h}' for (w, h) in allowed.keys()])
        raise ValueError(f'Unsupported watchface resolution {size[0]}x{size[1]}. Allowed: {allowed_str}')

    return allowed[size]


def _extract_clock_id_from_src_folder(src_dir):
    """
    Extract clock id from folder name: first integer in [50000..65535].
    """
    base = os.path.basename(os.path.abspath(src_dir))
    for s in re.findall(r'\d+', base):
        try:
            v = int(s)
        except Exception:
            continue
        if 50000 <= v <= 65535:
            return v
    raise ValueError(f'--clock-id not provided and no id in folder name: {base} (expected 50000..65535)')


def cli_main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Generate ATS3085-S watchface _res from a source folder (pure Python deps).'
    )
    parser.add_argument('--clock-id', type=int, default=None, help='Clock id (50000..65535). If omitted, extracted from src folder name')
    parser.add_argument('--face-size', default=None, choices=g_clock_id_prefix_dict, help='Watch face size. If omitted, extracted from image in the bottom (first) layer')
    parser.add_argument('--thumbnail', default=None, help='Optional thumbnail image path to embed (overrides auto-detect)')
    parser.add_argument('--no-lz4', action='store_true', help='Disable LZ4 compression (enabled by default)')
    parser.add_argument('--idle', action='store_true', help="Use idle magic string (II@*24dG) instead of default (Sb@*O2GG)")
    parser.add_argument('--out', default=os.getcwd(), help='Output directory (default: current)')
    parser.add_argument('src', metavar='source-dir', help='Source folder containing config.json and layer images')

    args = parser.parse_args(argv)

    src_dir = os.path.abspath(args.src)
    if not os.path.isdir(src_dir):
        raise NotADirectoryError(f'Source is not a directory: {src_dir}')

    # Clock ID
    clock_id_base = args.clock_id if args.clock_id is not None else _extract_clock_id_from_src_folder(src_dir)
    if not (50000 <= int(clock_id_base) <= 65535):
        raise ValueError(f'--clock-id must be in [50000..65535], got {clock_id_base}')

    # Detect resolution from first layer image and enforce watch face size
    clock_size = args.face_size if args.face_size is not None else _detect_clock_size_from_first_layer(src_dir)

    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)

    use_lz4 = not args.no_lz4

    ok = gen_clock_res(
        src_dir,
        out_dir,
        clock_id_base,
        clock_size,
        is_compress=use_lz4,
        idle_magic=args.idle,
        thumbnail_path_override=args.thumbnail
    )
    if not ok:
        raise SystemExit(2)

    return 0


if __name__ == '__main__':
    mp.freeze_support()
    logger_config()
    raise SystemExit(cli_main())
