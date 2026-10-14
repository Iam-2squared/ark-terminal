"""Exchange sessions are supplied by a dated, hashed calendar; never D-1 days."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from .exact_math import V2Error

JST = ZoneInfo("Asia/Tokyo")


@dataclass(frozen=True)
class ExchangeCalendar:
    sessions: tuple[date, ...]
    source_hash: str
    evidence_kind: str

    def __post_init__(self) -> None:
        if not self.sessions or self.sessions != tuple(sorted(set(self.sessions))):
            raise V2Error("INVALID_EXCHANGE_CALENDAR")
        if len(self.source_hash) != 64 or self.evidence_kind not in {"OFFICIAL", "SYNTHETIC"}:
            raise V2Error("CALENDAR_PROVENANCE_REQUIRED")

    def previous(self, session: date) -> date:
        if session not in self.sessions:
            raise V2Error("NON_EXCHANGE_SESSION")
        index = self.sessions.index(session)
        if index == 0:
            raise V2Error("UNKNOWN_PREVIOUS_EXCHANGE_SESSION")
        return self.sessions[index - 1]

    def history(self, session: date, count: int) -> tuple[date, ...]:
        if session not in self.sessions:
            raise V2Error("NON_EXCHANGE_SESSION")
        index = self.sessions.index(session)
        if count <= 0 or index < count:
            raise V2Error("UNKNOWN_REQUIRED_HISTORY")
        return self.sessions[index - count:index]


def cutoff(session: date) -> datetime:
    return datetime.combine(session, time(8, 50), JST)


def phase_times(session: date) -> tuple[datetime, datetime]:
    new = session >= date(2024, 11, 5)
    return (datetime.combine(session, time(15, 25) if new else time(15, 0), JST),
            datetime.combine(session, time(15, 30) if new else time(15, 0), JST))


def tick_in_window(event: datetime, session: date, minutes: int, phase: str) -> bool:
    if minutes not in {1, 5, 15, 30, 60}:
        raise V2Error("UNREGISTERED_ENGINEERING_WINDOW")
    end, _ = phase_times(session)
    if event.tzinfo is None or event.astimezone(JST).date() != session:
        raise V2Error("TICK_SESSION_TIME_MISMATCH")
    if end - timedelta(minutes=minutes) <= event <= end and phase == "UNKNOWN":
        raise V2Error("BOUNDARY_PHASE_UNKNOWN")
    return phase == "CONTINUOUS" and end - timedelta(minutes=minutes) <= event < end


def dependency_history() -> dict[str, int]:
    ma_periods = (5, 15, 25, 75)
    return {"g1": max(ma_periods) + 1, "g2": 75 + 2,
            "ema_macd": 150, "sma75_slope15": 75 + 15,
            "sma75_up_fraction3": 75 + 3, "rsi14": 75 + 1}
