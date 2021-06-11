#!/usr/bin/python
from __future__ import print_function
import struct
import time
import sys
import json

idx = sys.argv[1] if len(sys.argv) > 1 else "0"
infile_path = "/dev/input/event%s" % idx

"""
FORMAT represents the format used by linux kernel input event struct
See https://github.com/torvalds/linux/blob/v5.5-rc5/include/uapi/linux/input.h#L28
Stands for: long int, long int, unsigned short, unsigned short, unsigned int
"""
FORMAT = 'llHHi'
EVENT_SIZE = struct.calcsize(FORMAT)
DEBUG = False

#open file in binary mode
in_file = open(infile_path, "rb")

print(2)

def readfile(filename):
    try:
        with open(filename) as f:
            return f.read().strip()
    except IOError:
        return ""

def get_bits_int(x, offset=0):
    bits = []
    i = offset
    n = 1
    while n <= x:
        if n & x:
            bits.append(i)
        i += 1
        n <<= 1
    return bits

def get_bits(filename):
    s = readfile(filename)
    offset = 0
    bits = []
    for x in reversed(s.split()):
        bits += get_bits_int(int(x, 16), offset)
        offset += 64
    return bits


# ioctl(6, 0x80084502 /* EVIOCGID */, {bustype=5, vendor=1133, product=45085, version=34}) = 0
# ioctl(6, 0x81004506 /* EVIOCGNAME(256) */, "Logitech MX Ergo Multi-Device Trackball \0") = 41
# ioctl(6, 0x81004507 /* EVIOCGPHYS(256) */, "48:f1:7f:dc:e4:65\0") = 18
# ioctl(6, 0x81004508 /* EVIOCGUNIQ(256) */, "d5:9f:6a:d1:45:c2\0") = 18
# ioctl(6, 0x80044501 /* EVIOCGVERSION */, [0x10001]) = 0
# ioctl(6, 0x80044520 /* EVIOCGBIT(0, 4) */, [0 /* EV_SYN */, 0x1 /* EV_KEY */, 0x2 /* EV_REL */, 0x4 /* EV_MSC */] /* [0x847f882000000017] */) = 4
# ioctl(6, 0x80604520 /* EVIOCGBIT(0, 96) */, [0 /* EV_SYN */, 0x1 /* EV_KEY */, 0x2 /* EV_REL */, 0x4 /* EV_MSC */] /* [0x17] */) = 8
# ioctl(6, 0x80604521 /* EVIOCGBIT(EV_KEY, 96) */, [0x110 /* BTN_LEFT */, 0x111 /* BTN_RIGHT */, 0x112 /* BTN_MIDDLE */, 0x113 /* BTN_SIDE */, 0x114 /* BTN_EXTRA */, 0x115 /* BTN_FORWARD */, 0x116 /* BTN_BACK */, 0x117 /* BTN_TASK */, 0x118 /* KEY_??? */, 0x119 /* KEY_??? */, 0x11a /* KEY_??? */, 0x11b /* KEY_??? */, 0x11c /* KEY_??? */, 0x11d /* KEY_??? */, 0x11e /* KEY_??? */, 0x11f /* KEY_??? */] /* [0, 0, 0, 0, 0xffff0000, 0, 0, 0, 0, 0, 0, 0] */) = 96
# ioctl(6, 0x80604522 /* EVIOCGBIT(EV_REL, 96) */, [0 /* REL_X */, 0x1 /* REL_Y */, 0x6 /* REL_HWHEEL */, 0x8 /* REL_WHEEL */, 0xb /* REL_WHEEL_HI_RES */, 0xc /* REL_HWHEEL_HI_RES */] /* [0x1943] */) = 8
# ioctl(6, 0x80604524 /* EVIOCGBIT(EV_MSC, 96) */, [0x4 /* MSC_SCAN */] /* [0x10] */) = 8
# ioctl(6, 0x80044584 /* EVIOCGEFFECTS */, [0]) = 0
#
# ioctl(6, 0x80604520 /* EVIOCGBIT(0, 96) */, [0 /* EV_SYN */, 0x5 /* EV_SW */] /* [0x21] */) = 8
#
# [{"name": "Logitech MX Ergo Multi-Device Trackball ", "capabilities": {"1": [272, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 287], "2": [0, 1, 6, 8, 11, 12], "4": [4]}, "vendor": 1133, "product": 45085}]

sys_prefix = "/sys/class/input/event%s/device/" % idx

infos = {}
infos['name'] = readfile(sys_prefix + "name")
infos['vendor'] = int(readfile(sys_prefix + "id/vendor"), 16)
infos['product'] = int(readfile(sys_prefix + "id/product"), 16)

types = get_bits(sys_prefix + "capabilities/ev")
types_to_file = {
        0: "syn", 1: "key", 2: "rel", 3: "abs", 4: "msc", 5: "sw",
        0x11: "led", 0x12: "snd", 0x14: "rep", 0x15: "ff",
        0x16: "pwr", 0x17: "ff_status",
}
capabilities = {}
for type in types:
    if type not in types_to_file:
        print("unknown capability %d, skipping" % type, file=sys.stderr)
        continue
    bits = get_bits(sys_prefix + "capabilities/" + types_to_file[type])
    if bits:
        capabilities[type] = bits
infos['capabilities'] = capabilities


print(json.dumps([infos]))


event = in_file.read(EVENT_SIZE)

while event:
    (tv_sec, tv_usec, type, code, value) = struct.unpack(FORMAT, event)

    if DEBUG:
        if type != 0 or code != 0 or value != 0:
            print("Event type %u, code %u, value %u at %d.%d" % \
                (type, code, value, tv_sec, tv_usec))
        else:
            # Events with code, type and value == 0 are "separator" events
            print("===========================================")
    else:
        print("[0, %i, %i, %i]" % (type, code, value))

    event = in_file.read(EVENT_SIZE)

in_file.close()
