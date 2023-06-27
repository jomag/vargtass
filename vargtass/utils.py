from math import cos, pi, sin


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def print_hex(data: bytes):
    per_row = 16
    per_split = 8

    for i in range(0, len(data), per_row):
        chunk = data[i : i + per_row]

        adr = f"{i:04x}"
        char_values = [chr(b) if b >= 32 and b < 128 else "." for b in chunk]

        splits = [c for c in chunks(chunk, per_split)]

        hex_splits = [" ".join([f"{b:02X}" for b in spl]) for spl in splits]
        hex_values = "  ".join(hex_splits)

        char_values = "".join(char_values)
        pad1 = "   " * ((per_row - len(chunk)) % per_row)
        pad2 = " " * (per_row // per_split - len(splits))

        print(f"{adr}:  {hex_values}{pad1}{pad2}  {char_values}")


def print_header(hdr: str, underline: str = "-"):
    print(f"{hdr}\n{underline * len(hdr)}")


def rotate(x: float, y: float, angle: float):
    dx = cos(angle) * x - sin(angle) * y
    dy = sin(angle) * x + cos(angle) * y
    return dx, dy


def d2r(degrees: float):
    return degrees * (pi / 180.0)
