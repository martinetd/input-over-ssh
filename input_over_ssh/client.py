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

import argparse
import asyncio
import evdev
import json

async def do_forward_device(i, device):
	async for event in device.async_read_loop():
		print(json.dumps([i, event.type, event.code, event.value]))

async def forward_device(i, device):
	if args.exclusive:
		with device.grab_context():
			await do_forward_device(i, device)
	else:
		await do_forward_device(i, device)

def encode_device(device):
	cap = device.capabilities()
	del cap[0] # Filter out EV_SYN, otherwise we get OSError 22 Invalid argument
	cap_json = {}
	for k, v in cap.items():
		cap_json[k] = [x if not isinstance(x, tuple) else [x[0], x[1]._asdict()] for x in v]
	return {'name': device.name, 'capabilities': cap_json, 'vendor': device.info.vendor, 'product': device.info.product}

async def run_forward():
	# Find devices
	devices_by_name = {}
	if args.device_by_name:
		for path in evdev.list_devices():
			device = evdev.InputDevice(path)
			devices_by_name[device.name] = device
	
	devices = []
	for path in args.device_by_path:
		devices.append(evdev.InputDevice(path))
	for name in args.device_by_name:
		devices.append(devices_by_name[name])
	
	# Report version
	print(PROTOCOL_VERSION)
	
	# Report devices
	print(json.dumps([encode_device(device) for device in devices]))
	
	tasks = []
	for i, device in enumerate(devices):
		tasks.append(asyncio.create_task(forward_device(i, device)))
	
	await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

async def list_devices():
	for path in evdev.list_devices():
		device = evdev.InputDevice(path)
		print('{}  {}'.format(device.path, device.name))

parser = argparse.ArgumentParser(description='input-over-ssh client')
parser.add_argument('-L', '--list-devices', dest='action', action='store_const', const=list_devices, help='List available input devices')
parser.add_argument('-p', '--device-by-path', action='append', default=[], help='Forward device with the given path')
parser.add_argument('-n', '--device-by-name', action='append', default=[], help='Forward device with the given name')
parser.add_argument('-e', '--exclusive', action='store_true', help='Grab the device for exclusive input')
args = parser.parse_args()

if not args.action:
	args.action = run_forward

asyncio.run(args.action())
