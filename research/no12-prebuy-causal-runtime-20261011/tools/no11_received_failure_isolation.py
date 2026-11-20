"""Stop new Shadow BUY on entry/source failure, keep the existing EXIT path.

This is not brokerage recovery. Every position and fill remains simulated.
A halt is persisted in the existing portfolio transaction/event chain; restart
never clears it. Bad market data cannot generate a structural exit or fill.
"""
from __future__ import annotations

import re
import sqlite3

import no11_observed_execution_shadow as original
import no11_h235_asof_forward_shadow as h

ERRORS = (OSError, ValueError, KeyError, TypeError, RuntimeError, sqlite3.Error)


def settings(*args, **kwargs):
    return original.settings(*args, **kwargs)


def reason_code(error):
    reason = str(error)
    return reason if re.fullmatch(r'(?:NO11|P1_RSS|P1_FORWARD)_[A-Z0-9_]+', reason) else 'NO11_ENTRY_PIPELINE_FAILURE'


class ExecutionShadow(original.ExecutionShadow):
    @property
    def entry_halted(self):
        return self.portfolio.state().get('entryPipelineHalt') is True

    def halt_entry(self, reason, at):
        if not re.fullmatch(r'(?:NO11|P1_RSS|P1_FORWARD)_[A-Z0-9_]+', reason):
            reason = 'NO11_ENTRY_PIPELINE_FAILURE'

        def reducer(state):
            state['entryPipelineHalt'] = True
            reasons = set(state.get('entryPipelineHaltReasons', []))
            reasons.add(reason)
            state['entryPipelineHaltReasons'] = sorted(reasons)
            return {'status': 'ENTRY_HALTED_EXIT_REMAINS_AVAILABLE', 'reason': reason}
        # Existing private event machinery supplies atomicity and replay locks.
        return self.portfolio._event('ENTRY_PIPELINE_HALT:' + h.digest(reason),
                                     {'reason': reason}, at, reducer)

    def _cancel_known_buys(self, at):
        for order in self.portfolio.state()['orders'].values():
            if order['side'] == 'BUY' and order['status'] in {'INTENT', 'ACKNOWLEDGED', 'PARTIAL'}:
                self.portfolio.cancel(order['orderId'], at)

    def heartbeat(self, at):
        if self.entry_halted:
            self._cancel_known_buys(at)
        return super().heartbeat(at)

    def exit_only(self, feed, at):
        """Existing State9/EXIT only, with no H235 result or Capital funding."""
        original.need(self.entry_halted, 'EXIT_ONLY_REQUIRES_PERSISTED_ENTRY_HALT')
        now = h.timestamp(at, self.session)
        original.need(h.digest(self.previous) == self.feed_pin, 'PREVIOUS_SOURCE_CHANGED')
        # Validate source identity, receipt clocks and accepted historical rows
        # BEFORE marks, fills or State9 changes. Invalid feed leaves clock-only
        # EOD handling available to guarded_inference(), not fake market data.
        quotes = self._quotes(feed, now)
        self._verify_held_prefix(feed)
        self._cancel_known_buys(at)
        self._simulated_updates(quotes, at)
        self.portfolio.mark(quotes, at)
        traces = self._position_traces(feed)
        self.portfolio.evaluate_exits(traces, at)
        return self.summary()

    def advance(self, feed, inference, at):
        if self.entry_halted:
            return self.exit_only(feed, at)
        return super().advance(feed, inference, at)

    def summary(self):
        result = super().summary()
        state = self.portfolio.state()
        result.update(entryPipelineHalted=state.get('entryPipelineHalt') is True,
                      entryPipelineHaltReasons=state.get('entryPipelineHaltReasons', []),
                      realBrokerRecoveryCertified=False)
        return result


def guarded_inference(execution, feed, infer, *, clock, p1_summary):
    """One service iteration; never classify a failed entry path as success.

    Interrupts and process exits are intentionally not caught. Ledger failure
    also remains fatal: no fake healthy report when durable state is unavailable.
    """
    failure = None
    try:
        if execution.entry_halted:
            failure = 'NO11_ENTRY_PIPELINE_ALREADY_HALTED'
            summary = None
        else:
            summary = infer()
            paper = execution.advance(feed, summary, clock())
            return summary, paper
    except ERRORS as error:
        failure = reason_code(error)
        execution.halt_entry(failure, clock())
    try:
        paper = execution.exit_only(feed, clock())
        exit_status = 'VALIDATED_FEED_EXIT_ONLY'
    except ERRORS as error:
        execution.halt_entry(reason_code(error), clock())
        paper = execution.heartbeat(clock())
        exit_status = 'NO_VALID_FEED_CLOCK_ONLY'
    summary = {'schemaId': 'ARK_NO11_ENTRY_PIPELINE_HALTED_V1',
               'status': 'ENTRY_PIPELINE_HALTED', 'failureCode': failure,
               'exitStatus': exit_status, 'p1Session': p1_summary(),
               'h235OriginalModelExecutions': 0,
               'productionReady': False, 'orderTransmission': False}
    return summary, paper
