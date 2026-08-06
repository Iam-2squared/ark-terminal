from tools.rss_order_dryrun import build_rss_order_dry_run


def ready_context():
    return {
        "approval": {"status": "DRY_RUN_READY"},
        "risk": {"status": "DRY_RUN_ALLOWED"},
        "kill_switch": {"status": "ARMED"},
    }


def test_builds_preview_without_side_effects():
    result = build_rss_order_dry_run(
        {
            "symbol": "7203",
            "side": "BUY",
            "quantity": 100,
            "orderType": "LIMIT",
            "limitPrice": 2500,
        },
        **ready_context(),
        generated_at="2026-08-06T00:00:00+00:00",
    )

    assert result["status"] == "DRY_RUN_COMPLETED"
    assert result["excelPreview"]["cells"]["B2"] == "7203"
    assert result["excelPreview"]["cells"]["B9"] is False
    assert result["excelPreview"]["triggerValue"] is False
    assert result["sideEffects"] == {
        "excelWrites": 0,
        "triggerChanges": 0,
        "brokerWrites": 0,
        "liveOrders": 0,
    }
    assert result["safety"]["brokerWriteAllowed"] is False
    assert result["safety"]["liveTradingAllowed"] is False


def test_blocks_when_phase27_gates_are_not_ready():
    result = build_rss_order_dry_run(
        {
            "symbol": "9432.T",
            "side": "SELL",
            "quantity": 100,
            "orderType": "MARKET",
        }
    )

    assert result["status"] == "BLOCKED"
    assert "TWO_STEP_APPROVAL_INCOMPLETE" in result["blockers"]
    assert "RISK_GOVERNOR_BLOCKED" in result["blockers"]
    assert "KILL_SWITCH_HALTED" in result["blockers"]
    assert result["excelPreview"]["cells"]["B9"] is False


def test_rejects_invalid_limit_order():
    result = build_rss_order_dry_run(
        {
            "symbol": "4755.T",
            "side": "BUY",
            "quantity": 100,
            "orderType": "LIMIT",
            "limitPrice": 0,
        },
        **ready_context(),
    )

    assert result["status"] == "BLOCKED"
    assert "LIMIT_PRICE_INVALID" in result["blockers"]
    assert result["excelPreview"] is None


def test_audit_hash_is_deterministic_for_same_payload():
    kwargs = ready_context()
    first = build_rss_order_dry_run(
        {
            "symbol": "9984.T",
            "side": "BUY",
            "quantity": 100,
            "orderType": "LIMIT",
            "limitPrice": 10000,
        },
        **kwargs,
        generated_at="2026-08-06T00:00:00+00:00",
    )
    second = build_rss_order_dry_run(
        {
            "symbol": "9984.T",
            "side": "BUY",
            "quantity": 100,
            "orderType": "LIMIT",
            "limitPrice": 10000,
        },
        **kwargs,
        generated_at="2026-08-06T00:00:00+00:00",
    )

    assert first["auditHash"] == second["auditHash"]
