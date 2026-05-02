"""Unit tests for ERD-grounding heuristics on structured threat output."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from qa.qa_chain import (  # noqa: E402
    ThreatAnalysisItem,
    ThreatModelReport,
    _enforce_erd_grounding_on_report,
    _threat_row_anchors_context,
)


def test_anchor_accepts_verbatim_substring():
    ctx = "The PaymentIntent table stores cardholder data and links to MerchantAccount."
    assert _threat_row_anchors_context(
        erd_reference="PaymentIntent",
        affected_asset="",
        boundary_name="",
        threat_title="",
        context_blob=ctx,
    )


def test_anchor_accepts_two_distinct_tokens_from_row():
    ctx = "service foodesk connects to barn repository for orders"
    assert _threat_row_anchors_context(
        erd_reference="",
        affected_asset="foodesk",
        boundary_name="barn",
        threat_title="",
        context_blob=ctx,
    )


def test_anchor_rejects_fabricated_entity():
    ctx = "Only UserSession and AuditLog appear in this schema."
    assert not _threat_row_anchors_context(
        erd_reference="QuantumWalletLedger",
        affected_asset="QuantumWalletLedger",
        boundary_name="",
        threat_title="Fake",
        context_blob=ctx,
    )


def test_enforce_drops_ungrounded_rows():
    ctx = "Entity CustomerEmail stores plaintext contact."
    report = ThreatModelReport(
        scope_summary="test",
        threat_analysis=[
            ThreatAnalysisItem(
                boundary_name="DB",
                threat_title="SQL injection on CustomerEmail",
                affected_asset="CustomerEmail",
                control_name="param queries",
                description="…",
                severity="High",
                erd_reference="CustomerEmail",
                grounding_basis="document_anchored",
            ),
            ThreatAnalysisItem(
                boundary_name="Internet",
                threat_title="Generic nation-state APT",
                affected_asset="Unknown satellite bus",
                control_name="none",
                description="…",
                severity="Critical",
                erd_reference="made-up-component-xyz",
                grounding_basis="document_anchored",
            ),
        ],
        assets=[],
        actors=[],
        key_controls=[],
        residual_risk_rating="Medium",
        assumptions=[],
        sources=[],
        discarded_ungrounded=[],
    )
    out = _enforce_erd_grounding_on_report(report, ctx)
    assert len(out.threat_analysis) == 1
    assert out.threat_analysis[0].threat_title.startswith("SQL injection")
    assert len(out.discarded_ungrounded) == 1
    assert "nation-state" in out.discarded_ungrounded[0] or "made-up" in out.discarded_ungrounded[0]
