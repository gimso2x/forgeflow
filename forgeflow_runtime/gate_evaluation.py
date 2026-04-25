from __future__ import annotations


def required_finalize_flags(route: list[str], finalize_flags: list[str]) -> list[str]:
    required = list(finalize_flags)
    if "spec-review" not in route and "spec_review_approved" in required:
        required.remove("spec_review_approved")
    if "quality-review" not in route and "quality_review_approved" in required:
        required.remove("quality_review_approved")
    return required
