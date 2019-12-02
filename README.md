# input-over-ssh

Forwarding arbitrary input devices over SSH, such as gamepads/game controllers, mice and keyboards. Includes support for relative mouse pointer movement. See [here](https://yingtongli.me/blog/2019/12/01/input-over-ssh-2.html) for additional background and discussion.

(For the legacy implementation using xinput/xdotool, see the [legacy branch](https://yingtongli.me/git/input-over-ssh/tree/?h=legacy).)

## Usage

To use input-over-ssh, download input-over-ssh on both the client and server, and install [python-evdev](https://pypi.org/project/evdev/) as a dependency.

Then navigate to the root directory on the client and run:

```
python -m input_over_ssh.client -L
```

This will print a list of all available evdev devices. If no devices appear, ensure the current user has access to the raw */dev/input* device files (e.g. by adding the user to the *input* group).

Then pass the path of the device to be forwarded, and pipe the output to an instance of input-over-ssh running on the server. Also pass the `-u` flag to Python when running the client, to force unbuffered output. For example:

```
python -u -m input_over_ssh.client -p /dev/input/event1 | ssh hostname.example.com 'PYTHONPATH=/path/to/input-over-ssh python -m input_over_ssh.server'
```

For the adventurous, you ought to be able to replace ssh with netcat/socat over UDP to further reduce latency.

For a full list of command-line options, run `python -m input_over_ssh.client --help`.
