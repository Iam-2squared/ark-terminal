"""Test-process audit hook. Kernel socket prohibition is installed by the launcher."""
import os
import sys
import json
import atexit

if os.environ.get('ARK_TEST_OFFLINE') == '1':
    folder = os.environ.get('ARK_OFFLINE_AUDIT_DIR')
    if not folder or not os.path.isdir(folder):
        os._exit(98)
    file = os.path.join(folder, f'python-{os.getpid()}.jsonl')
    blocked = 0

    def record(value):
        with open(file, 'a') as stream:
            stream.write(json.dumps(value) + '\n')

    def hook(event, args):
        global blocked
        if event in ('socket.connect', 'socket.getaddrinfo', 'socket.gethostbyname', 'socket.gethostbyaddr', 'socket.sendto'):
            blocked += 1
            record({'event': 'BLOCKED_BEFORE_NETWORK', 'api': event})
            raise RuntimeError('ARK_OFFLINE_NETWORK_FORBIDDEN:' + event)

    def finish():
        record({'event': 'GUARD_EXIT', 'blockedAttempts': blocked})
        if blocked:
            os._exit(97)

    record({'event': 'GUARD_LOADED'})
    sys.addaudithook(hook)
    atexit.register(finish)
