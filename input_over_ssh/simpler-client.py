#!/usr/bin/python
from __future__ import print_function
import struct
import sys
import json
import fcntl

idx = sys.argv[1] if len(sys.argv) > 1 else "3"
infile_path = "/dev/input/event%s" % idx

"""
FORMAT represents the format used by linux kernel input event struct
See https://github.com/torvalds/linux/blob/v5.5-rc5/include/uapi/linux/input.h#L28
Stands for: long int, long int, unsigned short, unsigned short, unsigned int
"""
FORMAT = 'llHHi'
EVENT_SIZE = struct.calcsize(FORMAT)
DEBUG = (len(sys.argv) > 2)

KB_MAPPING = {
    28: 28,    # return
    103: 103,  # up
    105: 105,  # left
    106: 106,  # right
    108: 108,  # down
    114: 114,  # volumedown
    115: 115,  # volumeup
    # 402 -> chanup
    # 403 -> chandown
}

infos = [
    {
        'name': 'keyboard',
        'capabilities': {
            1: list(KB_MAPPING.values()),
        },
        'vendor': 1,
        'product': 1,
    },
    {
        'name': 'mouse',
        'capabilities': {
            1: [272, 330],  # click, touch (probably don't need)
            2: [8],    # scroll
            3: [[0, [0, 0, 1920, 0, 0, 1]], [1, [0, 0, 1080, 0, 0, 1]]],
        },
        'vendor': 2,
        'product': 2,
    },
]

print(2)
print(json.dumps(infos))

# open file in binary mode
in_file = open(infile_path, "rb")

# grab device, this is EVIOCGRAB
fcntl.ioctl(in_file, 0x40044590, 1)

event = in_file.read(EVENT_SIZE)

while event:
    (tv_sec, tv_usec, type, code, value) = struct.unpack(FORMAT, event)

    if type == 0 and code == 0 and value == 0:
        pass
    elif type == 1 and code == 1198:
        print("[1, 1, 330, 0]")
    elif type == 1 and code == 1199:
        print("[1, 1, 330, 1]")
    elif type == 1 and code == 272:
        # mouse left click: OK as is
        print("[1, %i, %i, %i]" % (type, code, value))
    elif type == 1 and code in KB_MAPPING:
        # "keyboard" keys
        print("[0, %i, %i, %i]" % (type, KB_MAPPING[code], value))
    elif type == 3:
        print("[1, %i, %i, %i]" % (type, code, value))
    else:
        print("Unhandled key: type %i, code %i, value %i at %d.%06d" %
              (type, code, value, tv_sec, tv_usec),
              file=sys.stderr)
    if DEBUG:
        print("Event: type %i, code %i (-> %i), value %i at %d.%06d" %
              (type, code, KB_MAPPING[code] if code in KB_MAPPING else code,
               value, tv_sec, tv_usec),
              file=sys.stderr)
    sys.stdout.flush()

    event = in_file.read(EVENT_SIZE)

in_file.close()
