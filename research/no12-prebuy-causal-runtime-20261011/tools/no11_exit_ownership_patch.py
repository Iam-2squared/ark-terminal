"""Stage a narrowly pinned EXIT dispatch guard; never enable trading.

The existing coordinator already excludes external symbols and checks actual
broker holdings. Its _dispatch boundary did not reread the observer after
preparing a batch. This patch adds that check, without adopting manual fills,
changing the ledger or Frozen EXIT strategy, sending orders, or editing Excel.
The default CLI only audits. --output writes a NEW service file for an isolated
staging installation, never overwriting the source or the live installation.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
from pathlib import Path

ORIGINAL_BLOB = '9fe2be9835c06605f9c15177eecc49bdf6a931f3'
MARKER = 'EXIT_OWNERSHIP_RECHECK_V1'
ANCHOR = '''    def _dispatch(self, command, at):
        # IN_FLIGHT is committed before invoking any process/sink. Neither a
        # restart nor a missing result can issue this command a second time.
        permit = self.book.begin_dispatch(command['commandId'], at)['dispatchPermit']
'''
REPLACEMENT = '''    def _exit_ownership_before_dispatch(self, command, at):
        # EXIT_OWNERSHIP_RECHECK_V1: manual shares are never adopted here.
        # This runs BEFORE IN_FLIGHT and the only irreversible transport.
        if command['kind'] != 'ORDER' or command['side'] != 'SELL':
            return at
        if self.config['evidenceMode'] == 'BROKER_OBSERVATION':
            need(self.observe_file(at), 'EXIT_FRESH_BROKER_OBSERVATION_REQUIRED')
            at = self.clock()
        state = self.book.snapshot(at)
        order = state['orders'].get(command['intentId'])
        need(type(order) is dict and
             order['commandId'] == command['commandId'] and
             all(order.get(k) == command.get(k)
                 for k in ('symbol', 'side', 'quantity', 'account')),
             'EXIT_RECORDED_ORDER_REQUIRED')
        position = state['positions'].get(order['entryId'])
        need(type(position) is dict and
             position['symbol'] == order['symbol'] and
             position['account'] == order['account'] and
             0 < order['quantity'] <= position['quantity'],
             'EXIT_NOT_REMAINING_ARK_OWNED')
        # Existing checks enforce fresh source, sticky personal-symbol
        # exclusion, same-account actual holding and external sell reservation.
        self._sell_safe(order, at)
        return at

    def _dispatch(self, command, at):
        at = self._exit_ownership_before_dispatch(command, at)
        # IN_FLIGHT is committed before invoking any process/sink. Neither a
        # restart nor a missing result can issue this command a second time.
        permit = self.book.begin_dispatch(command['commandId'], at)['dispatchPermit']
'''


def git_blob(text: str) -> str:
    data = text.encode('utf-8')
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


def patch_text(source: str) -> str:
    """Return the exact reviewed patch or fail; accept only our idempotent result."""
    source = source.replace('\r\n', '\n')
    if MARKER in source:
        if source.count(REPLACEMENT) != 1:
            raise ValueError('NO11_EXIT_PATCH_PREEXISTING_CHANGE_REQUIRES_REVIEW')
        restored = source.replace(REPLACEMENT, ANCHOR)
        if git_blob(restored) != ORIGINAL_BLOB:
            raise ValueError('NO11_EXIT_PATCH_OTHER_SOURCE_CHANGED')
        ast.parse(source)
        return source
    if git_blob(source) != ORIGINAL_BLOB or source.count(ANCHOR) != 1:
        raise ValueError('NO11_EXIT_PATCH_PINNED_SOURCE_MISMATCH')
    result = source.replace(ANCHOR, REPLACEMENT)
    ast.parse(result)
    return result


def stage(source_path: Path, output_path: Path | None = None) -> str:
    if (not source_path.is_file() or source_path.is_symlink()
            or any(p.is_symlink() for p in source_path.parents)):
        raise ValueError('NO11_EXIT_PATCH_SOURCE_UNSAFE')
    original = source_path.read_text(encoding='utf-8')
    result = patch_text(original)
    if output_path is not None:
        if (not output_path.is_absolute() or not output_path.parent.is_dir()
                or output_path.exists() or output_path.is_symlink()
                or any(p.is_symlink() for p in output_path.parents)
                or output_path.resolve() == source_path.resolve()):
            raise ValueError('NO11_EXIT_PATCH_NEW_ISOLATED_OUTPUT_REQUIRED')
        # Exclusive creation prevents replacing a running service by accident.
        with output_path.open('xb') as handle:
            handle.write(result.encode('utf-8'))
            handle.flush()
    return git_blob(result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path,
                        default=Path(__file__).with_name('no11_broker_execution_service.py'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    digest = stage(args.source, args.output)
    print('NO11_EXIT_OWNERSHIP_SOURCE=PINNED_AND_PATCHABLE')
    print('NO11_EXIT_OWNERSHIP_PATCHED_BLOB=' + digest)
    print('NO11_EXIT_OWNERSHIP_STAGE=' + ('NEW_FILE_ONLY' if args.output else 'AUDIT_ONLY'))
    print('LIVE_INSTALLATION_MODIFIED=False')
    print('ORDER_TRANSMISSION=False')


if __name__ == '__main__':
    main()
