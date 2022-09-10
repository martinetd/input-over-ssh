#!/usr/bin/env python3
#   input-over-ssh: Forwarding arbitrary input devices over SSH
#   Copyright © 2019  Lee Yingtong Li (RunasSudo)
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

import sys
import os

import site
v = sys.version_info
site.addsitedir(f"/run/current-system/sw/lib/python{v.major}.{v.minor}/site-packages")

import evdev
import json
from optparse import OptionParser


parser = OptionParser()
parser.add_option('--pidfile', action='store', type='string',
                  help="pid file to kill old process if set")

(options, args) = parser.parse_args()

if (options.pidfile and options.pidfile.endswith('.pid')
      and options.pidfile.startswith('/run/')
      and '..' not in options.pidfile):
    try:
        with open(options.pidfile, 'r') as pidfile:
            oldpid = pidfile.read().strip()
            with open('/proc/%s/cmdline' % oldpid, 'r') as cmdline:
                if sys.argv[0] in cmdline.read():
                    os.kill(int(oldpid), 15)
    except FileNotFoundError:
        pass
    with open(options.pidfile, 'w') as pidfile:
        pidfile.write("%d\n" % os.getpid())

PROTOCOL_VERSION = '2'

version = input()
if version[-1] != PROTOCOL_VERSION:
    raise Exception('Invalid protocol version. Got {}, expected {}.'.format(version, PROTOCOL_VERSION))

devices_json = json.loads(input())
devices = []
for device_json in devices_json:
    capabilities = {}
    for k, v in device_json['capabilities'].items():
        capabilities[int(k)] = v
    devices.append(evdev.UInput(capabilities, name=device_json['name'] + ' (via input-over-ssh)', vendor=device_json['vendor'], product=device_json['product']))

print('Device created')

while True:
    event = json.loads(input())
    #print(event)
    devices[event[0]].write(event[1], event[2], event[3])
    devices[event[0]].syn()
