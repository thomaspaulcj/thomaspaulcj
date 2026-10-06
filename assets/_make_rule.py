"""Build a thin theme-aware animated rule for the profile README."""

from pathlib import Path

WIDTH = 480
HEIGHT = 3
FRAMES = 48
LINE_ROW = 1


def lzw(indices, min_code_size=2):
    clear = 1 << min_code_size
    eoi = clear + 1
    emitted = []

    def init():
        return {bytes([i]): i for i in range(clear)}, eoi + 1, min_code_size + 1

    table, next_code, width = init()
    emitted.append((clear, width))
    word = b""
    for byte in indices:
        key = word + bytes([byte])
        if key in table:
            word = key
            continue
        emitted.append((table[word], width))
        if next_code == 4096:
            emitted.append((clear, width))
            table, next_code, width = init()
        else:
            table[key] = next_code
            next_code += 1
            if next_code == (1 << width) and width < 12:
                width += 1
        word = bytes([byte])
    if word:
        emitted.append((table[word], width))
    emitted.append((eoi, width))

    acc = 0
    bits = 0
    out = bytearray()
    for code, size in emitted:
        acc |= code << bits
        bits += size
        while bits >= 8:
            out.append(acc & 0xFF)
            acc >>= 8
            bits -= 8
    if bits:
        out.append(acc & 0xFF)
    return bytes(out)


def sub_blocks(data):
    parts = []
    for i in range(0, len(data), 255):
        chunk = data[i : i + 255]
        parts.append(bytes([len(chunk)]) + chunk)
    parts.append(b"\x00")
    return b"".join(parts)


def frame_pixels(offset, track, pulse, edge):
    pixels = bytearray(WIDTH * HEIGHT)
    start = offset % WIDTH
    span = WIDTH // 5
    for x in range(WIDTH):
        dist = (x - start) % WIDTH
        if dist < 2 or dist > span - 2:
            color = edge if dist < span else track
        elif dist < span:
            color = pulse
        else:
            color = track
        pixels[LINE_ROW * WIDTH + x] = color
    return pixels


def gif(frames, palette):
    # palette index 0 is transparent
    gct = b"".join(bytes(rgb) for rgb in palette)
    header = b"GIF89a"
    lsd = (
        WIDTH.to_bytes(2, "little")
        + HEIGHT.to_bytes(2, "little")
        + bytes([0xF1, 0x00, 0x00])
    )
    loop = b"!\xFF\x0BNETSCAPE2.0\x03\x01\xFF\xFF\x00"
    body = b""
    for pixels in frames:
        compressed = lzw(pixels)
        gce = b"!\xF9\x04" + bytes([0x09, 8, 0, 0, 0])  # 8 cs, transparent index 0
        descriptor = (
            b"\x2C"
            + (0).to_bytes(2, "little")
            + (0).to_bytes(2, "little")
            + WIDTH.to_bytes(2, "little")
            + HEIGHT.to_bytes(2, "little")
            + b"\x00"
        )
        body += gce + descriptor + bytes([2]) + sub_blocks(compressed)
    return header + lsd + gct + loop + body + b";"


def build(path, track, pulse, edge):
    frames = [frame_pixels(int(i * WIDTH / FRAMES), 1, 2, 3) for i in range(FRAMES)]
    palette = [(0, 0, 0), track, pulse, edge]
    path.write_bytes(gif(frames, palette))


out = Path(__file__).resolve().parent
build(out / "rule-light.gif", (208, 215, 222), (9, 105, 218), (140, 180, 230))
build(out / "rule-dark.gif", (48, 54, 61), (88, 166, 255), (40, 90, 160))
