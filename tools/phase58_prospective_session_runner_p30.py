from __future__ import annotations

import phase58_prospective_session_runner as p17


_ORIGINAL_BUILD = p17.build_cycle_commands


def build_cycle_commands_p30(**kwargs):
    commands = _ORIGINAL_BUILD(**kwargs)
    if not commands or len(commands[0]) < 2:
        raise RuntimeError("P17 export command shape changed")
    commands[0][1] = "tools/phase58_excel_5m_chart_export_stable.py"
    return commands


def main() -> int:
    # Reuse the frozen P17 orchestration, freshness budget, finite-cycle behavior,
    # and READ ONLY safety surface. P30 changes only the RssChart exporter invoked.
    p17.build_cycle_commands = build_cycle_commands_p30
    return p17.main()


if __name__ == "__main__":
    raise SystemExit(main())
