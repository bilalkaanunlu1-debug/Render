"""Generate fallback MEGA FAV PNG icons without third-party graphics libraries."""
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parent

def inside_polygon(x, y, vertices):
    inside = False
    j = len(vertices) - 1
    for i in range(len(vertices)):
        xi, yi = vertices[i]
        xj, yj = vertices[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside

def chunk(tag, data):
    return struct.pack('!I', len(data)) + tag + data + struct.pack('!I', zlib.crc32(tag + data) & 0xffffffff)

def render(size):
    mark = [(64, 18), (78, 49), (110, 64), (78, 79), (64, 111), (50, 79), (18, 64), (50, 49)]
    pixels = bytearray()
    for y in range(size):
        pixels.append(0)
        for x in range(size):
            xx, yy = (x + 0.5) * 128 / size, (y + 0.5) * 128 / size
            color = (17, 22, 41)
            if (xx - 64) ** 2 + (yy - 64) ** 2 <= 51 ** 2:
                color = (32, 31, 73)
            if inside_polygon(xx, yy, mark):
                color = (182, 168, 255)
            pixels.extend(color + (255,))
    data = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!IIBBBBB', size, size, 8, 6, 0, 0, 0))
    data += chunk(b'IDAT', zlib.compress(bytes(pixels), level=9)) + chunk(b'IEND', b'')
    return data

for size, filename in [(180, 'apple-touch-icon.png'), (192, 'icon-192.png'), (512, 'icon-512.png')]:
    target = ROOT / 'static' / filename
    if not target.is_file():
        target.write_bytes(render(size))
        print(f'Created {filename}')
