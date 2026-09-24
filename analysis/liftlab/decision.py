"""Section 10 application (analysis-plan Deviations 2026-09-24, 1e-1f) and the recommendation object.

Inputs: effects_primary.json (full-sample Section 6 estimates) and targeting.json (the single holdout
evaluation). Every text field is a template filled with values from those files; none is hand-typed.
"""

from __future__ import annotations

from typing import Any

from liftlab.models import DEFAULT_COST, MENS, NONE, WOMENS

COST_GRID: list[float] = [round(0.01 * i, 2) for i in range(1, 51)]
EMAIL_CONTRAST: dict[str, str] = {MENS: "H1", WOMENS: "H2"}
POLICY_EMAILS: dict[str, list[str]] = {"P0": [], "P1": [MENS], "P2": [WOMENS]}
SEND, PROMISING, DO_NOT = "send", "promising — test again", "do not send"

TEMPLATES: dict[str, str] = {
    "blanket_send": (
        "Send the {email} to every customer: in the full experiment it added {estimate} of revenue per customer "
        "({level} CI {ci_low} to {ci_high}), against an assumed send cost of {cost} per email{targeting_clause}."
    ),
    "blanket_promising": (
        "The {email} is promising but not yet proven at an assumed {cost} per email: it added {estimate} of revenue "
        "per customer ({level} CI {ci_low} to {ci_high}), so test it again at larger scale before sending to everyone."
    ),
    "targeted": (
        "Send emails according to policy {policy} ({policy_description}): on the holdout it added {holdout_net} of net "
        "revenue per customer over sending nothing ({level} CI {holdout_low} to {holdout_high}) at an assumed {cost} per email."
    ),
    "targeted_downgrade": "Under Section 10 the following emails are {status} rather than send: {emails}.",
    "none": "Do not send: no email policy produced positive net revenue at an assumed {cost} per email.",
    "targeting_beat": "",
    "targeting_not_beat": "; on the untouched holdout, no targeting policy beat sending to everyone",
    "margin": (
        "Supplementary, not pre-registered: at {cost} per email, sending pays if gross margin is at least {margin_point} "
        "(at the point estimate) or {margin_lower} (at the lower bound of the {level} CI)."
    ),
}


def money(x: float) -> str:
    return f"{'−' if x < 0 else ''}${abs(x):,.2f}"


def pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def status(estimate: float, lower: float, cost: float) -> str:
    if lower > cost:
        return SEND
    if estimate > cost:
        return PROMISING
    return DO_NOT


def email_table(primary: dict[str, Any], cost: float) -> dict[str, Any]:
    out = {}
    for email, cid in EMAIL_CONTRAST.items():
        c = next(x for x in primary["contrasts"] if x["id"] == cid)
        est, lo, hi = c["estimate"], c["ci_analytic"][0], c["ci_analytic"][1]
        out[email] = {
            "contrast": cid,
            "incremental_revenue_per_customer": est,
            "ci_analytic": [lo, hi],
            "ci_bootstrap": c["ci_bootstrap"],
            "status": status(est, lo, cost),
            "status_if_bootstrap_bound": status(est, c["ci_bootstrap"][0], cost),
            "break_even_cost_at_estimate": est,
            "break_even_cost_at_lower_bound": lo,
            "break_even_cost_at_bootstrap_lower_bound": c["ci_bootstrap"][0],
            "minimum_margin_at_estimate": cost / est if est > 0 else None,
            "minimum_margin_at_lower_bound": cost / lo if lo > 0 else None,
        }
    return out


def sensitivity(emails: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for c in COST_GRID:
        row: dict[str, Any] = {"cost": c}
        for email, e in emails.items():
            est, lo = e["incremental_revenue_per_customer"], e["ci_analytic"][0]
            row[email] = {"net_at_estimate": est - c, "net_at_lower_bound": lo - c, "status": status(est, lo, c)}
        rows.append(row)
    return rows


def recommendation(primary: dict[str, Any], targeting: dict[str, Any], emails: dict[str, Any], cost: float) -> dict[str, Any]:
    """Rule 1d winner, with each email it sends carrying its 1e status (Deviations 2026-09-24)."""
    level = f"{primary['confidence_level'] * 100:.0f}%"
    winner = targeting["winner"]["winner"]
    row = next(r for r in targeting["policies"] if r["policy"] == winner)
    sends = POLICY_EMAILS.get(winner)
    holdout = {
        "policy": winner,
        "net_value_vs_p0": row["net_value_vs_p0"],
        "net_value_vs_p0_ci": row["net_value_vs_p0_ci"],
        "incremental_revenue_vs_p0": row["incremental_revenue_vs_p0"],
        "incremental_revenue_vs_p0_ci": row["incremental_revenue_vs_p0_ci"],
        "share_sent": row["share_sent"],
    }
    if winner == "P0":
        kind, email_status = "none", {}
        text = TEMPLATES["none"].format(cost=money(cost))
    elif sends is not None:
        email = sends[0]
        e = emails[email]
        email_status = {email: e["status"]}
        values = {
            "email": email, "estimate": money(e["incremental_revenue_per_customer"]), "level": level,
            "ci_low": money(e["ci_analytic"][0]), "ci_high": money(e["ci_analytic"][1]), "cost": money(cost),
            "targeting_clause": TEMPLATES["targeting_beat" if targeting["winner"]["targeting_beat_blanket"] else "targeting_not_beat"],
        }
        kind = "blanket_send" if e["status"] == SEND else "blanket_promising"
        text = TEMPLATES[kind].format(**values)
    else:
        share = row["action_share"]
        email_status = {a: emails[a]["status"] for a in (MENS, WOMENS) if share[a] > 0}
        downgraded = any(s != SEND for s in email_status.values())
        kind = "targeted"
        text = TEMPLATES["targeted"].format(
            policy=winner, policy_description=", ".join(f"{a} to {pct(share[a])}" for a in (MENS, WOMENS, NONE)),
            holdout_net=money(row["net_value_vs_p0"]), level=level,
            holdout_low=money(row["net_value_vs_p0_ci"][0]), holdout_high=money(row["net_value_vs_p0_ci"][1]), cost=money(cost))
        if downgraded:
            text += " " + TEMPLATES["targeted_downgrade"].format(
                status=PROMISING, emails=", ".join(a for a, st in email_status.items() if st != SEND))
    margin_email = sends[0] if sends else None
    margin_text = None
    if margin_email and emails[margin_email]["minimum_margin_at_lower_bound"] is not None:
        e = emails[margin_email]
        margin_text = TEMPLATES["margin"].format(cost=money(cost), margin_point=pct(e["minimum_margin_at_estimate"]),
                                                 margin_lower=pct(e["minimum_margin_at_lower_bound"]), level=level)
    return {
        "kind": kind,
        "policy": winner,
        "emails_sent": sends if sends is not None else [a for a in (MENS, WOMENS) if row["action_share"][a] > 0],
        "email_status": email_status,
        "targeting_beat_blanket": targeting["winner"]["targeting_beat_blanket"],
        "cost_assumption": cost,
        "sentence": text,
        "supplementary_margin_sentence": margin_text,
        "holdout": holdout,
        "templates": TEMPLATES,
    }


def decide(primary: dict[str, Any], targeting: dict[str, Any], cost: float = DEFAULT_COST) -> dict[str, Any]:
    emails = email_table(primary, cost)
    return {
        "cost": cost,
        "confidence_level": primary["confidence_level"],
        "interval": "Welch analytic 95% CI from Section 6 (bootstrap bound reported alongside)",
        "status_rule": {"send": "lower bound > cost", "promising — test again": "point estimate > cost >= lower bound",
                        "do not send": "otherwise"},
        "emails": emails,
        "sensitivity": sensitivity(emails),
        "margin_view": {
            "supplementary": True,
            "pre_registered": False,
            "note": "Presentation aid derived from pre-registered quantities; the data contains no margin.",
            "definition": "minimum gross margin = cost / incremental revenue per customer",
        },
        "winner": {**targeting["winner"],
                   "holdout": next({"net_value_vs_p0": r["net_value_vs_p0"], "net_value_vs_p0_ci": r["net_value_vs_p0_ci"]}
                                   for r in targeting["policies"] if r["policy"] == targeting["winner"]["winner"])},
        "evaluated_at_code_commit_sha": targeting["evaluated_at_code_commit_sha"],
        "recommendation": recommendation(primary, targeting, emails, cost),
    }
