#!/usr/bin/python
# coding=utf-8

"""
stream events from input device, without depending on evdev
"""
from __future__ import print_function
import struct
import sys
import os
import time
import json
import fcntl
import errno
import select
import signal

from optparse import OptionParser
import subprocess

parser = OptionParser()
parser.add_option('-c', '--command', action='store', type='string',
                  help='write to command stdin, or stdout by default')
parser.add_option('-v', '--verbose', action='count')
parser.add_option('-e', '--event', action='store', type='string', default='0',
                  help='event number e.g. 3 for /dev/input/event3 (default 0)')
parser.add_option('-p', '--pidfile', action='store', type='string',
                  help='pidfile, also kills old instance if existed')
parser.add_option('-D', '--daemonize', action='store_true',
                  help='close files and daemonizes. requires -c')

(options, args) = parser.parse_args()

if (options.pidfile and options.pidfile.endswith('.pid')
        and options.pidfile.startswith('/run/')
        and '..' not in options.pidfile):
    try:
        with open(options.pidfile, 'r') as pidfile:
            oldpid = pidfile.read().strip()
            with open('/proc/%s/cmdline' % oldpid, 'r') as cmdline:
                if __file__ in cmdline.read():
                    os.kill(int(oldpid), 15)
    except EnvironmentError as err:
        if err.errno == errno.ENOENT:
            pass
        else:
            raise
else:
    options.pidfile = None

infile_path = "/dev/input/event%s" % options.event
outfile = sys.stdout
outproc = None

"""
FORMAT represents the format used by linux kernel input event struct. See
https://github.com/torvalds/linux/blob/v5.5-rc5/include/uapi/linux/input.h#L28
Stands for: long int, long int, unsigned short, unsigned short, unsigned int
"""
FORMAT = 'llHHi'
EVENT_SIZE = struct.calcsize(FORMAT)
DEBUG = options.verbose

KB_MAPPINGS = {
    28: 28,    # return
    103: 103,  # up
    105: 105,  # left
    106: 106,  # right
    108: 108,  # down
    113: 113,  # mute
    114: 74,   # volumedown -> - (keypad)
    115: 78,   # volumeup -> + (keypad)
    139: 16,   # settings -> q = queue
    272: 28,   # left click when no mouse -> return
    362: 23,   # bangumihyou -> i = info
    401: 26,   # blue corner: [
    398: 27,   # red corner: ]
    399: 33,   # green corner: f (+alt)
    400: 17,   # yellow corner: w (+alt)
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

KB_MODIFIERS = {
    399: 56,  # green corner: alt (+f)
    400: 56,  # yellow corner: alt (+w)
}

INPUT_SLEEP = [241, 834, 873, 835, 874]  # source, 2, 3
INPUT_WAKE = [833, 872]   # 1

BUGGY_MOUSE_KEYS = [139, 362, 773]  # setting, bangumihyou, home

infos = [
    {
        'name': 'keyboard',
        'capabilities': {
            1: list(KB_MAPPINGS.values()) + list(KB_MODIFIERS.values()),
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


class Output():
    def __init__(self, command, infos):
        self.command = command
        self.infos = infos
        if not command:
            self.outfile = sys.stdout
            return
        self.outproc = None
        self.reconnect()

    def reconnect(self):
        if self.outproc:
            self.outproc.wait()
        self.outproc = subprocess.Popen(self.command, shell=True,
                                        stdin=subprocess.PIPE)
        self.outfile = self.outproc.stdin
        print(2, file=self.outfile)
        print(json.dumps(self.infos), file=self.outfile)
        self.outfile.flush()

    def close(self, *args):
        if self.outproc:
            if not self.outproc.poll():
                self.outproc.terminate()
        sys.exit(0)

    def write(self, line):
        try:
            print(line, file=self.outfile)
            self.outfile.flush()
            if DEBUG > 0:
                print(line, file=sys.stderr)
        except IOError:
            # XXX check errno = 32 (broken pipe)
            if not self.command:
                raise
            self.reconnect()
            self.write(line)


# open file in binary mode
in_file = open(infile_path, "rb")

retries = 10
while retries > 0:
    try:
        # grab device, this is EVIOCGRAB
        fcntl.ioctl(in_file, 0x40044590, 1)
        break
    except IOError:
        # device busy? XXX kill old and try again?
        # continue for now
        if retries <= 1:
            print("Could not grab, aborting", file=sys.stderr)
            sys.exit(1)
    retries -= 1
    time.sleep(0.2)

if options.daemonize:
    if not options.command:
        print("Cannot daemonize if no command!", file=sys.stderr)
        sys.exit(1)
    devnull = open('/dev/null', 'w+')
    #sys.stdout = devnull
    #sys.stderr = devnull
    sys.stdin.close()
    if os.fork() != 0:
        sys.exit(0)
    if os.fork() != 0:
        sys.exit(0)

if options.pidfile:
    with open(options.pidfile, 'w') as pidfile:
        pidfile.write("%d\n" % os.getpid())

output = Output(options.command, infos)

signal.signal(signal.SIGTERM, output.close)

class State():
    sleeping = False
    wake_last_ts = 0

    def suspend(self):
        self.sleeping = True
        # ungrab
        fcntl.ioctl(in_file, 0x40044590, 0)

    def resume(self):
        self.sleeping = False
        # grab
        fcntl.ioctl(in_file, 0x40044590, 1)


class Mouse():
    ok = False
    skip_next = False

    def convert(self, evtype, code, value):
        if evtype == 1 and code == 1198:
            # "pen" touch down
            self.ok = True
            if value == 0:
                self.skip_next = True
            return (1, 330, 0)
        if evtype == 1 and code == 1199:
            # "pen" touch up
            self.ok = False
            if value == 0:
                self.skip_next = True
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
            self.skip_next = False
            return True
        output.write("[1, %i, %i, %i]" % (evtype, code, value))
        return True


mouse = Mouse()
state = State()

def parse(tv_sec, tv_usec, evtype, code, value):
    if DEBUG == 2:
        print("Event: type %i, code %i (-> %i), value %i at %d.%06d" %
              (evtype, code,
               KB_MAPPINGS[code] if code in KB_MAPPINGS else code,
               value, tv_sec, tv_usec),
              file=sys.stderr)

    if state.sleeping:
        if evtype == 1 and code in INPUT_WAKE:
            if value == 1:
                state.wake_last_ts = time.time()
            else:
                if time.time() - state.wake_last_ts > 1:
                    print("Resume remote", file=sys.stderr)
                    state.resume()
        return

    if evtype == 0 and code == 0 and value == 0:
        pass
    elif evtype == 1 and code in INPUT_SLEEP:
        print("Suspend remote", file=sys.stderr)
        state.suspend()
        return
    elif mouse.input(evtype, code, value):
        # it printed
        pass
    elif evtype == 1 and code in KB_MAPPINGS:
        # "keyboard" keys
        if code in BUGGY_MOUSE_KEYS:
            mouse.skip_next = True
        if value == 1 and code in KB_MODIFIERS:
            output.write("[0, 1, %i, 1]" % KB_MODIFIERS[code])
        output.write("[0, 1, %i, %i]" % (KB_MAPPINGS[code], value))
        if value == 0 and code in KB_MODIFIERS:
            output.write("[0, 1, %i, 0]" % KB_MODIFIERS[code])
        mouse.ok = False
    else:
        print("Unhandled key: type %i, code %i, value %i at %d.%06d" %
              (evtype, code, value, tv_sec, tv_usec),
              file=sys.stderr)
    sys.stdout.flush()


def check_freespace():
    try:
        stat = os.statvfs('/tmp/usb/sda/sda1/')
    except OSError:
        return
    # if not mounted yet we'll get tmpfs stats,
    # since we can't get fstype detect this with smaller total size
    total_gb = stat.f_blocks * stat.f_bsize / 1024 / 1024 / 1024
    if total_gb < 100:
        return
    # and actual left size check
    left_gb = stat.f_bavail * stat.f_bsize / 1024 / 1204 / 1024
    if left_gb < 40:
        msg = "ディスクの容量が少ない（%d GB)" % (left_gb)
        json = '{ "message": "%s", "buttons": [{"label": "Ok"}]}' % (msg)
        cmd = "luna-send -n 1 luna://com.webos.notification/createAlert '%s'" % (json)
        os.system(cmd)

# init worked: we can now default to suspended state
state.suspend()

DISK_CHECK_INTERVAL = 900
# first check fast
next_disk_check = time.time() + 10

while True:
    timeout = next_disk_check - time.time()
    if timeout <= 0:
        check_freespace()
        next_disk_check = time.time() + DISK_CHECK_INTERVAL
        continue

    (ready, _, _) = select.select([in_file], [], [], timeout)
    if in_file in ready:
        event = in_file.read(EVENT_SIZE)
        parse(*struct.unpack(FORMAT, event))

in_file.close()
