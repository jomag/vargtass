# References:
#
# "Wolfenstein 3D game file specifications"
# https://vpoupet.github.io/wolfenstein/docs/files.html
#
# ModdingWiki:
# https://moddingwiki.shikadi.net/wiki/GameMaps_Format

from dataclasses import dataclass
import logging
import os

import pygame

from .utils import chunks, print_header, print_hex


def to_u16(data: bytes, offset: int = 0):
    return data[offset] | (data[offset + 1] << 8)


def to_u32(data: bytes, offset: int = 0):
    return to_u16(data, offset) | (to_u16(data, offset + 2) << 16)


def decompress_rlew(data: bytes, rlew_tag: int):
    de = bytearray()
    idx = 0

    def pop():
        nonlocal idx
        idx += 2
        return data[idx - 2] + (data[idx - 1] << 8)

    size = pop()

    while idx < len(data):
        v = pop()
        if v == rlew_tag:
            n, r = pop(), pop()
            for _ in range(n):
                de.append(r & 0xFF)
                de.append(r >> 8)
        else:
            de.append(v & 0xFF)
            de.append(v >> 8)

    if len(de) != size:
        raise Exception(f"Decompressed size mismatch: expected {size}, got {len(de)}")

    return de


def decompress_carmack(data: bytes):
    NEAR_POINTER = 0xA7
    FAR_POINTER = 0xA8

    def pop():
        nonlocal idx
        idx += 1
        return data[idx - 1]

    de = bytearray()
    idx = 0
    size = pop() + (pop() << 8)

    while idx < len(data):
        n, kw = pop(), pop()
        if kw in (NEAR_POINTER, FAR_POINTER):
            if n == 0:
                de.append(pop())
                de.append(kw)
            else:
                if kw == NEAR_POINTER:
                    offs = len(de) - pop() * 2
                else:
                    offs = (pop() + (pop() << 8)) * 2
                de.extend(de[offs : offs + n * 2])
        else:
            de.append(n)
            de.append(kw)

    if len(de) != size:
        raise Exception(f"Decompressed size mismatch: expected {size}, got {len(de)}")

    return de


class Plane:
    width: int
    height: int
    map: list[int]

    def __init__(self, map: bytes, width: int, height: int):
        assert len(map) == width * height * 2
        self.width, self.height = width, height
        self.map = [to_u16(map, i) for i in range(0, len(map), 2)]

    def get_cell(self, x: int, y: int):
        return self.map[y * self.width + x]

    # Returns true if the given cell is "solid" (wall or similar)
    def is_solid(self, x: int, y: int):
        # TODO: 64 is not correct, but it works for now
        return self.get_cell(x, y) < 64


class Plane0(Plane):
    """Plane 0 contains structural information"""

    def print(self):
        def to_char(n: int):
            if 0 <= n <= 63:
                return "W"
            if 90 <= n <= 91:
                return "P"
            if 92 <= n <= 93:
                return "G"
            if 94 <= n <= 95:
                return "S"
            if 100 <= n <= 101:
                return "E"
            if 106 <= n <= 143:
                return "."
            return "?"

        for row in chunks(self.map, self.width):
            print("".join(to_char(n) for n in row))


class Plane1(Plane):
    """Plane 1 contains locations for things"""

    def print(self):
        def to_char(n: int):
            if 19 <= n <= 22:
                return "S"
            if 23 <= n <= 70:
                return "P"
            if n == 29:
                return "D"
            if 43 <= n <= 44:
                return "K"
            if n == 47:
                return "F"
            if n == 48:
                return "M"
            if n == 49:
                return "A"
            if n == 50:
                return "m"
            if n == 51:
                return "c"
            if 52 <= n <= 55:
                return "T"
            if n == 56:
                return "L"
            if n == 124:
                return "x"
            if n == 98:
                return "W"
            if 108 <= n <= 227:
                return "E"
            return " "

        for row in chunks(self.map, self.width):
            print("".join(to_char(n) for n in row))


class Plane2(Plane):
    """Plane 2 contains props"""

    # fmt: off
    blocking = [
        24, 25, 26, 28, 30, 31, 33, 34, 35, 36, 39,
        40, 41, 45, 58, 59, 60, 62, 63, 68, 69
    ]
    # fmt: on

    def print(self):
        def to_char(n: int):
            if n in self.blocking:
                return "B"
            return "."

        for row in chunks(self.map, self.width):
            print("".join(to_char(n) for n in row))


@dataclass
class LevelHeader:
    plane0_offset: int
    plane1_offset: int
    plane2_offset: int
    plane0_len: int
    plane1_len: int
    plane2_len: int
    width: int
    height: int
    name: str


class Level:
    header: LevelHeader
    plane0: Plane0
    plane1: Plane1
    plane2: Plane2

    def __init__(
        self, header: LevelHeader, plane0: Plane0, plane1: Plane1, plane2: Plane2
    ):
        self.header = header
        self.plane0 = plane0
        self.plane1 = plane1
        self.plane2 = plane2

    @property
    def width(self):
        return self.header.width

    @property
    def height(self):
        return self.header.height

    # Returns position and direction of the player spawn point
    def get_player_spawn(self):
        for y in range(self.height):
            for x in range(self.width):
                if self.plane1.get_cell(x, y) == 19:
                    return (x, y), 0
                if self.plane1.get_cell(x, y) == 20:
                    return (x, y), 90
                if self.plane1.get_cell(x, y) == 21:
                    return (x, y), 180
                if self.plane1.get_cell(x, y) == 22:
                    return (x, y), 270
        raise Exception("No player spawn point found in map")


class Media:
    walls: dict[int, list[int]]
    wall_surfaces: dict[int, pygame.Surface]
    sprites: dict[int, list[int]]
    sounds: dict[int, int]

    # fmt: off
    palette = [
        0x00000000, 0x000000A8, 0x0000A800, 0x0000A8A8, 0x00A80000, 0x00A800A8, 0x00A85400, 0x00A8A8A8,
        0x00545454, 0x005454FC, 0x0054FC54, 0x0054FCFC, 0x00FC5454, 0x00FC54FC, 0x00FCFC54, 0x00FCFCFC,
        0x00ECECEC, 0x00DCDCDC, 0x00D0D0D0, 0x00C0C0C0, 0x00B4B4B4, 0x00A8A8A8, 0x00989898, 0x008C8C8C,
        0x007C7C7C, 0x00707070, 0x00646464, 0x00545454, 0x00484848, 0x00383838, 0x002C2C2C, 0x00202020,
        0x00FC0000, 0x00EC0000, 0x00E00000, 0x00D40000, 0x00C80000, 0x00BC0000, 0x00B00000, 0x00A40000,
        0x00980000, 0x00880000, 0x007C0000, 0x00700000, 0x00640000, 0x00580000, 0x004C0000, 0x00400000,
        0x00FCD8D8, 0x00FCB8B8, 0x00FC9C9C, 0x00FC7C7C, 0x00FC5C5C, 0x00FC4040, 0x00FC2020, 0x00FC0000,
        0x00FCA85C, 0x00FC9840, 0x00FC8820, 0x00FC7800, 0x00E46C00, 0x00CC6000, 0x00B45400, 0x009C4C00,
        0x00FCFCD8, 0x00FCFCB8, 0x00FCFC9C, 0x00FCFC7C, 0x00FCF85C, 0x00FCF440, 0x00FCF420, 0x00FCF400,
        0x00E4D800, 0x00CCC400, 0x00B4AC00, 0x009C9C00, 0x00848400, 0x00706C00, 0x00585400, 0x00404000,
        0x00D0FC5C, 0x00C4FC40, 0x00B4FC20, 0x00A0FC00, 0x0090E400, 0x0080CC00, 0x0074B400, 0x00609C00,
        0x00D8FCD8, 0x00BCFCB8, 0x009CFC9C, 0x0080FC7C, 0x0060FC5C, 0x0040FC40, 0x0020FC20, 0x0000FC00,
        0x0000FC00, 0x0000EC00, 0x0000E000, 0x0000D400, 0x0004C800, 0x0004BC00, 0x0004B000, 0x0004A400,
        0x00049800, 0x00048800, 0x00047C00, 0x00047000, 0x00046400, 0x00045800, 0x00044C00, 0x00044000,
        0x00D8FCFC, 0x00B8FCFC, 0x009CFCFC, 0x007CFCF8, 0x005CFCFC, 0x0040FCFC, 0x0020FCFC, 0x0000FCFC,
        0x0000E4E4, 0x0000CCCC, 0x0000B4B4, 0x00009C9C, 0x00008484, 0x00007070, 0x00005858, 0x00004040,
        0x005CBCFC, 0x0040B0FC, 0x0020A8FC, 0x00009CFC, 0x00008CE4, 0x00007CCC, 0x00006CB4, 0x00005C9C,
        0x00D8D8FC, 0x00B8BCFC, 0x009C9CFC, 0x007C80FC, 0x005C60FC, 0x004040FC, 0x002024FC, 0x000004FC,
        0x000000FC, 0x000000EC, 0x000000E0, 0x000000D4, 0x000000C8, 0x000000BC, 0x000000B0, 0x000000A4,
        0x00000098, 0x00000088, 0x0000007C, 0x00000070, 0x00000064, 0x00000058, 0x0000004C, 0x00000040,
        0x00282828, 0x00FCE034, 0x00FCD424, 0x00FCCC18, 0x00FCC008, 0x00FCB400, 0x00B420FC, 0x00A800FC,
        0x009800E4, 0x008000CC, 0x007400B4, 0x0060009C, 0x00500084, 0x00440070, 0x00340058, 0x00280040,
        0x00FCD8FC, 0x00FCB8FC, 0x00FC9CFC, 0x00FC7CFC, 0x00FC5CFC, 0x00FC40FC, 0x00FC20FC, 0x00FC00FC,
        0x00E000E4, 0x00C800CC, 0x00B400B4, 0x009C009C, 0x00840084, 0x006C0070, 0x00580058, 0x00400040,
        0x00FCE8DC, 0x00FCE0D0, 0x00FCD8C4, 0x00FCD4BC, 0x00FCCCB0, 0x00FCC4A4, 0x00FCBC9C, 0x00FCB890,
        0x00FCB080, 0x00FCA470, 0x00FC9C60, 0x00F0945C, 0x00E88C58, 0x00DC8854, 0x00D08050, 0x00C87C4C,
        0x00BC7848, 0x00B47044, 0x00A86840, 0x00A0643C, 0x009C6038, 0x00905C34, 0x00885830, 0x0080502C,
        0x00744C28, 0x006C4824, 0x005C4020, 0x00543C1C, 0x00483818, 0x00403018, 0x00382C14, 0x0028200C,
        0x00600064, 0x00006464, 0x00006060, 0x0000001C, 0x0000002C, 0x00302410, 0x00480048, 0x00500050,
        0x00000034, 0x001C1C1C, 0x004C4C4C, 0x005C5C5C, 0x00404040, 0x00303030, 0x00343434, 0x00D8F4F4,
        0x00B8E8E8, 0x009CDCDC, 0x0074C8C8, 0x0048C0C0, 0x0020B4B4, 0x0020B0B0, 0x0000A4A4, 0x00009898,
        0x00008C8C, 0x00008484, 0x00007C7C, 0x00007878, 0x00007474, 0x00007070, 0x00006C6C, 0x00980088,
    ]
    # fmt: on

    def __init__(self):
        self.walls = {}
        self.wall_surfaces = {}

    # Adds a wall picture. The data should be the uncompressed image data, palette indexed.
    def add_wall(self, index: int, data: bytes):
        assert len(data) == 64 * 64, "Wall data must be 64x64 pixels"
        w = [self.palette[i] for i in data]
        self.walls[index] = w

    def get_wall_surface(self, index: int):
        try:
            return self.wall_surfaces[index]
        except KeyError:
            if index not in self.walls:
                return None
            wall = self.walls[index]
            surf = pygame.Surface((64, 64))
            pxarray = pygame.PixelArray(surf)
            wall = self.walls[index]
            for x in range(64):
                for y in range(64):
                    pxarray[y, x] = wall[y * 64 + x]  # type: ignore
            pxarray.close()
            self.wall_surfaces[index] = surf
            return surf


class GameAssets:
    rlew_tag: int
    level_offsets: list[int]
    level_headers: list[LevelHeader]
    media: Media

    def load_maphead(self, path: str):
        # TODO: the file format supports optional tile data after the level offsets.
        # This is however not used in Wolfenstein 3D, so it's not implemented here.
        data = open(path, "rb").read()
        self.rlew_tag = data[0] | (data[1] << 8)
        self.level_offsets = [to_u32(b) for b in chunks(data[2:], 4)]

    def load_gamemaps(self, path: str):
        data = open(path, "rb").read()
        if data[0:8] != b"TED5v1.0":
            raise Exception("Invalid GAMEMAPS header: missing TED5v1.0 signature")
        self.gamemaps = data

    def load_vswap(self, path: str):
        data = open(path, "rb").read()

        # Total chunk count
        tot = to_u16(data, 0)

        # First chunk that is a sprite
        first_sprite = to_u16(data, 2)

        # First chunk that is a sound
        first_sound = to_u16(data, 4)

        # Chunk offsets and lengths
        offsets = [to_u32(data, 6 + i * 4) for i in range(tot)]
        lengths = [to_u16(data, 6 + tot * 4 + i * 2) for i in range(tot)]

        self.media = Media()

        for i in range(first_sprite):
            if lengths[i] > 0:
                self.media.add_wall(i, data[offsets[i] : offsets[i] + lengths[i]])

    def load_level(self, level: int):
        o = self.level_offsets[level]
        hdr = LevelHeader(
            plane0_offset=to_u32(self.gamemaps, o + 0),
            plane1_offset=to_u32(self.gamemaps, o + 4),
            plane2_offset=to_u32(self.gamemaps, o + 8),
            plane0_len=to_u16(self.gamemaps, o + 12),
            plane1_len=to_u16(self.gamemaps, o + 14),
            plane2_len=to_u16(self.gamemaps, o + 16),
            width=to_u16(self.gamemaps, o + 18),
            height=to_u16(self.gamemaps, o + 20),
            name=self.gamemaps[o + 22 : o + 22 + 16].decode("ascii").rstrip("\0"),
        )

        map = self.gamemaps[hdr.plane0_offset : hdr.plane0_offset + hdr.plane0_len]
        map = decompress_carmack(map)
        map = decompress_rlew(map, self.rlew_tag)
        plane0 = Plane0(map, hdr.width, hdr.height)

        map = self.gamemaps[hdr.plane1_offset : hdr.plane1_offset + hdr.plane1_len]
        map = decompress_carmack(map)
        map = decompress_rlew(map, self.rlew_tag)
        plane1 = Plane1(map, hdr.width, hdr.height)

        map = self.gamemaps[hdr.plane2_offset : hdr.plane2_offset + hdr.plane2_len]
        map = decompress_carmack(map)
        map = decompress_rlew(map, self.rlew_tag)
        plane2 = Plane2(map, hdr.width, hdr.height)

        return Level(header=hdr, plane0=plane0, plane1=plane1, plane2=plane2)

    def print(self):
        print_header("MapHead")
        print("rlew_tag:     0x%04X" % self.rlew_tag)
        for lvl in range(0, 100, 10):
            print(
                f"Level {lvl:02d}-{(lvl+9):02d}:  "
                + "  ".join(f"0x{o:04X}" for o in self.level_offsets[lvl : lvl + 10])
            )

    def print_level(self, nlevel: int):
        offset = self.level_offsets[nlevel]

        print_header(f"Level {nlevel} (offset 0x{offset:04X}):")
        level = self.load_level(nlevel)
        print("Name: %s" % level.header.name)
        print("Width: %d" % level.header.width)
        print("Height: %d" % level.header.height)
        po, pl = level.header.plane0_offset, level.header.plane0_len
        print(f"Plane 0 - offset: 0x{po:04X}, length: 0x{pl:02X} ({pl})")
        po, pl = level.header.plane1_offset, level.header.plane1_len
        print(f"Plane 1 - offset: 0x{po:04X}, length: 0x{pl:02X} ({pl})")
        po, pl = level.header.plane2_offset, level.header.plane2_len
        print(f"Plane 2 - offset: 0x{po:04X}, length: 0x{pl:02X} ({pl})")
        print("")
        print_header("Plane 0")
        level.plane0.print()
        print_header("Plane 1")
        level.plane1.print()
        print_header("Plane 2")
        level.plane2.print()

    def load(self, path: str):
        logging.info("Loading MAPHEAD.WL1 (map offsets)")
        self.load_maphead(os.path.join(path, "MAPHEAD.WL1"))

        logging.info("Loading GAMEMAPS.WL1 (maps)")
        self.load_gamemaps(os.path.join(path, "GAMEMAPS.WL1"))

        logging.info("Loading VSWAP (textures, sprites, sounds)")
        self.load_vswap(os.path.join(path, "VSWAP.WL1"))
