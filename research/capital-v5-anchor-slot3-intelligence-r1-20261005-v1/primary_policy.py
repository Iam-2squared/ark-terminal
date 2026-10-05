"""R1 pure intervention policy. No execution books or evaluation identity access."""
from dataclasses import dataclass
from fractions import Fraction
import math

HEADS = ('pP', 'MOVE_U2', 'MOVE_U3', 'MRET')
RANK_NAMES = ('rP', 'r2', 'r3', 'rM')
VETO_REASON = 'V5_SLOT3_UNANIMOUS_LOW_SHIELD_REJECT'
ABSTAIN_REASON = 'INTELLIGENCE_UNAVAILABLE_ABSTAIN_TO_V5'
RESERVE_REASON = 'SLOT3_RESERVE_FOR_FUTURE_QUALITY'
ARMS = ('OFF', 'D', 'DR')

@dataclass(frozen=True)
class Rank:
    numerator: int
    denominator: int
    available: bool = True

    @property
    def low(self):
        return self.available and 2 * self.numerator < self.denominator

    @property
    def high(self):
        return self.available and not self.low

    @property
    def fraction(self):
        if not self.available:
            raise ValueError('INTELLIGENCE_UNAVAILABLE')
        return Fraction(self.numerator, self.denominator)

    def audit(self):
        return {'numerator': self.numerator, 'denominator': self.denominator,
                'LOW': self.low, 'HIGH': self.high, 'available': self.available}

def rank_from_scores(current, training):
    """Strict less count. Invalid current never becomes LOW or HIGH."""
    if current is None or not math.isfinite(float(current)):
        return Rank(0, 1, False)
    values = tuple(training)
    if not values or any(not math.isfinite(float(value)) for value in values):
        return Rank(0, 1, False)
    return Rank(1 + sum(value < current for value in values), len(values) + 1)

def ranks_from_record(record):
    """Consumes only four causal score/rank contracts, never outcome metadata."""
    result = []
    for head in HEADS:
        item = record.get(head) if record else None
        if not item or item.get('score') is None or not math.isfinite(float(item['score'])):
            result.append(Rank(0, 1, False)); continue
        if 'rank_numerator' in item and 'rank_denominator' in item:
            num, den = item['rank_numerator'], item['rank_denominator']
            if type(num) is not int or type(den) is not int or not 1 <= num <= den or den <= 1:
                raise ValueError('RANK_CONTRACT_INVALID')
            result.append(Rank(num, den))
        else:
            result.append(rank_from_scores(item['score'], item.get('training_scores', ())))
    return tuple(result)

@dataclass(frozen=True)
class CandidateView:
    entry_id: str
    native_rank: str
    native_admit: bool
    native_reason: str
    native_admission_index: int
    actual_planned_slot: int
    native_quantity: int
    ranks: tuple
    stable_order: int
    current_constraints_pass: bool = True

    def __post_init__(self):
        if len(self.ranks) != 4 or any(not isinstance(r, Rank) for r in self.ranks):
            raise ValueError('FOUR_RANKS_REQUIRED')

def direct_decision(view):
    if not all(rank.available for rank in view.ranks):
        return {'veto': False, 'reason': ABSTAIN_REASON}
    veto = (view.native_admit and view.native_admission_index == 3
            and view.actual_planned_slot == 3 and view.native_quantity >= 100
            and view.current_constraints_pass and all(rank.low for rank in view.ranks))
    return {'veto': veto, 'reason': VETO_REASON if veto else 'ABSTAIN_TO_V5'}

@dataclass(frozen=True)
class RecoveryToken:
    session: str
    created_minute: int
    origin_entry_id: str
    held_pair_ids: tuple
    active: bool = True

    def audit(self):
        return {'session': self.session, 'created_minute': self.created_minute,
                'origin_entry_id': self.origin_entry_id,
                'held_pair_ids': list(self.held_pair_ids), 'active': self.active}

def invalidate_token(token, session, minute, held_ids, session_end=False):
    if token is None:
        return None, None
    held = tuple(sorted(set(held_ids)))
    reason = ('SESSION_END' if session_end else 'SESSION_CHANGED' if session != token.session
              else 'CUTOFF' if minute >= 920 else 'OPEN_BELOW_TWO' if len(held) < 2
              else 'THIRD_BUY_SUCCESS' if len(held) > 2
              else 'HELD_PAIR_CHANGED' if held != token.held_pair_ids else None)
    return (None, reason) if reason else (token, None)

def create_token(token, session, minute, origin_entry_id, held_ids):
    held = tuple(sorted(set(held_ids)))
    if token is not None or len(held) != 2 or minute >= 920:
        return token, False
    return RecoveryToken(session, minute, origin_entry_id, held), True

def choose_recovery(token, session, minute, held_ids, native_picked_nonempty, candidates):
    """Returns at most one candidate before allocation; failed first has no fallback."""
    live, _ = invalidate_token(token, session, minute, held_ids)
    if live is None or minute <= live.created_minute or native_picked_nonempty:
        return None
    eligible = [candidate for candidate in candidates
                if candidate.entry_id != live.origin_entry_id
                and candidate.native_rank == 'B'
                and not candidate.native_admit
                and candidate.native_reason == RESERVE_REASON
                and candidate.current_constraints_pass
                and all(rank.high for rank in candidate.ranks)]
    if not eligible:
        return None
    def priority(candidate):
        ranks = candidate.ranks
        return (-ranks[0].fraction, -ranks[2].fraction, -ranks[3].fraction,
                -ranks[1].fraction, candidate.stable_order)
    return min(eligible, key=priority)

def rank_audit(ranks):
    return {name: rank.audit() for name, rank in zip(RANK_NAMES, ranks)}

# The decision input type cannot contain protected IDs, labels, execution books,
# High/return/EXIT suffixes, future availability, or teacher-membership vectors.
DECISION_INPUT_ALLOWLIST = tuple(CandidateView.__dataclass_fields__)
