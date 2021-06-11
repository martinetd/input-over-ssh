#!/usr/bin/python
"""
stream events from input device, without depending on evdev
"""
from __future__ import print_function
import struct
import sys
import time
import json
import fcntl

idx = sys.argv[1] if len(sys.argv) > 1 else "3"
infile_path = "/dev/input/event%s" % idx

"""
FORMAT represents the format used by linux kernel input event struct. See
https://github.com/torvalds/linux/blob/v5.5-rc5/include/uapi/linux/input.h#L28
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
    113: 113,  # mute
    114: 114,  # volumedown
    115: 115,  # volumeup
    139: 16,   # settings -> q = queue
    272: 28,   # left click when no mouse -> return
    362: 23,   # bangumihyou -> i = info
    402: 102,  # chanup -> home
    403: 107,  # chandown -> end
    412: 14,   # modoru -> backspace = back (to playing or parent folder)
    428: 57,   # mic -> space = play/pause
    773: 1,    # home -> ESC = home
    832: 50,   # BS/CS -> m = other context menu
    845: 50,   # BS/CS has 3 values
    858: 50,   # BS/CS has 3 values
    833: 2,    # 1
    834: 3,    # 2
    835: 4,    # 3
    836: 5,    # 4
    837: 6,    # 5
    838: 7,    # 6
    839: 8,    # 7
    840: 9,    # 8
    841: 10,   # 9
    842: 11,   # 10
    872: 2,    # 1
    873: 3,    # 2
    874: 4,    # 3
    875: 5,    # 4
    876: 6,    # 5
    877: 7,    # 6
    878: 8,    # 7
    879: 9,    # 8
    880: 10,   # 9
    881: 11,   # 10
    994: 46,   # sub -> c = context menu
    1037: 19,  # netflix -> r = rewind
    1038: 33,  # prime video -> f = fast forward
}

INPUT_SLEEP = 241  # source
INPUT_WAKE = [833, 872]   # 1

BUGGY_MOUSE_KEYS = [139, 362, 773]  # setting, bangumihyou, home

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
sys.stdout.flush()

# open file in binary mode
in_file = open(infile_path, "rb")

# grab device, this is EVIOCGRAB
try:
    fcntl.ioctl(in_file, 0x40044590, 1)
except IOError:
    # device busy? XXX kill old and try again?
    # continue for now
    print("grab failed, skipping", file=sys.stderr)

event = in_file.read(EVENT_SIZE)

class State():
    sleeping = False
    wake_last_ts = 0


class Mouse():
    ok = False
    skip_next = False

    def convert(self, evtype, code, value):
        if evtype == 1 and code == 1198:
            # "pen" touch down
            self.ok = True
            return (1, 330, 0)
        if evtype == 1 and code == 1199:
            # "pen" touch up
            self.ok = False
            return (1, 330, 1)
        if evtype == 1 and code in [272, 28] and self.ok:
            # left click, or enter
            return (1, 272, value)
        if evtype == 3:
            # absolute position
            if not self.ok:
                self.skip_next = True
            return (3, code, value)
        if evtype == 2 and code == 8:
            # wheel scroll
            self.ok = True
            return (2, 8, value)

        return (0, 0, 0)


    def input(self, evtype, code, value):
        (evtype, code, value) = self.convert(evtype, code, value)
        if evtype == 0:
            return False
        if self.skip_next:
            self.ok = False
            return True
        print("[1, %i, %i, %i]" % (evtype, code, value))
        return True


mouse = Mouse()
state = State()

def parse(tv_sec, tv_usec, evtype, code, value):
    if state.sleeping:
        if evtype == 1 and code in INPUT_WAKE:
            if value == 1:
                state.wake_last_ts = time.time()
            else:
                if time.time() - state.wake_last_ts > 1:
                    state.sleeping = False
                    print("Resume remote", file=sys.stderr)
                    fcntl.ioctl(in_file, 0x40044590, 1)
        return

    if evtype == 0 and code == 0 and value == 0:
        pass
    elif evtype == 1 and code == INPUT_SLEEP:
        state.sleeping = True
        print("Suspend remote", file=sys.stderr)
        # ungrab
        fcntl.ioctl(in_file, 0x40044590, 0)
        return
    elif mouse.input(evtype, code, value):
        # it printed
        pass
    elif evtype == 1 and code in KB_MAPPING:
        # "keyboard" keys
        if code in BUGGY_MOUSE_KEYS:
            mouse.skip_next = True
        print("[0, %i, %i, %i]" % (evtype, KB_MAPPING[code], value))
        mouse.ok = False
    else:
        print("Unhandled key: type %i, code %i, value %i at %d.%06d" %
              (evtype, code, value, tv_sec, tv_usec),
              file=sys.stderr)
    if DEBUG:
        print("Event: type %i, code %i (-> %i), value %i at %d.%06d" %
              (evtype, code, KB_MAPPING[code] if code in KB_MAPPING else code,
               value, tv_sec, tv_usec),
              file=sys.stderr)
    sys.stdout.flush()


while event:
    parse(*struct.unpack(FORMAT, event))

    event = in_file.read(EVENT_SIZE)

in_file.close()
