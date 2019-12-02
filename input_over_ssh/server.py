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

PROTOCOL_VERSION = '2'

import evdev
import json

version = input()
if version != PROTOCOL_VERSION:
	raise Exception('Invalid protocol version. Got {}, expected {}.'.format(version, PROTOCOL_VERSION))

devices_json = json.loads(input())
devices = []
for device_json in devices_json:
	capabilities = {}
	for k, v in device_json['capabilities'].items():
		capabilities[int(k)] = [x if not isinstance(x, list) else (x[0], evdev.AbsInfo(**x[1])) for x in v]
	devices.append(evdev.UInput(capabilities, name=device_json['name'] + ' (via input-over-ssh)', vendor=device_json['vendor'], product=device_json['product']))

print('Device created')

while True:
	event = json.loads(input())
	#print(event)
	devices[event[0]].write(event[1], event[2], event[3])
