#!/usr/bin/env python3
"""Linux-only fail-closed test launcher; deny Internet sockets before exec.

Filter is inherited across exec/fork and cannot be removed. No privileged setup,
network namespace, firewall changes, or changes to production defaults.
"""
import ctypes
import os
import platform
import resource
import sys


def lock_network():
    if sys.platform != 'linux' or platform.machine() != 'x86_64':
        raise RuntimeError('OFFLINE_KERNEL_GUARD_UNSUPPORTED_PLATFORM')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    lib = ctypes.CDLL('libseccomp.so.2')
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_syscall_resolve_name.restype = ctypes.c_int
    class Compare(ctypes.Structure):
        _fields_ = [('arg', ctypes.c_uint), ('op', ctypes.c_int),
                    ('datum_a', ctypes.c_uint64), ('datum_b', ctypes.c_uint64)]
    lib.seccomp_rule_add_array.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int,
                                          ctypes.c_uint, ctypes.POINTER(Compare)]
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    allow, kill_process = 0x7fff0000, 0x80000000
    ctx = lib.seccomp_init(allow)
    if not ctx:
        raise RuntimeError('OFFLINE_KERNEL_GUARD_INIT_FAILED')
    try:
        # SCMP_CMP_NE=1: all socket domains except AF_UNIX=1 are denied.
        # AF_UNIX socketpair remains usable for Python event-loop wakeup/IPC.
        # All connect calls are denied too, including Unix proxy connections.
        for name, comparison in [(b'socket', Compare(0, 1, 1, 0)), (b'connect', None)]:
            number = lib.seccomp_syscall_resolve_name(name)
            if number < 0:
                raise RuntimeError('OFFLINE_KERNEL_GUARD_SYSCALL_UNRESOLVED')
            result = lib.seccomp_rule_add_array(ctx, kill_process, number,
                1 if comparison is not None else 0, ctypes.byref(comparison) if comparison is not None else None)
            if result != 0:
                raise RuntimeError(f'OFFLINE_KERNEL_GUARD_RULE_FAILED:{result}')
        if lib.seccomp_load(ctx) != 0:
            raise RuntimeError('OFFLINE_KERNEL_GUARD_LOAD_FAILED')
    finally:
        lib.seccomp_release(ctx)


if __name__ == '__main__':
    if os.environ.get('ARK_TEST_OFFLINE') != '1' or len(sys.argv) < 2:
        raise RuntimeError('OFFLINE_EXPLICIT_TEST_LAUNCH_REQUIRED')
    lock_network()
    os.execvpe(sys.argv[1], sys.argv[1:], os.environ)
