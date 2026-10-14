"""Validate evidenced saved-original reuse, separately from data admission.

An owner's current-work renewal attestation is not an independently verified
provider entitlement or a subscription expiry date. It never authorizes new
acquisition, public data upload, protected outcome release or trading.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from preopen_io import require_safe_flags
from preopen_selector import CONTRACT, JST, PreopenError, stamp, digest

REPOSITORIES = frozenset((
    "Iam-2squared/J-quants-A", "Iam-2squared/J-quants-B",
    "Iam-2squared/J-Quants-C", "Iam-2squared/J-quants-D",
    "Iam-2squared/J-quants-E"))
OWNER_SCOPE = "PRIVATE_SAVED_ORIGINALS_CURRENT_WORK"
ATTESTATION_FRESHNESS = timedelta(hours=24)


def validate_reuse_authorization(evidence, *, work_id=None, now=None):
    """Return evidence classification; fail closed for missing/stale authority.

    The 24-hour bound is an engineering freshness guard, NOT the subscription's
    expiry. Expiry remains null when the owner has not supplied it. Future work
    cannot silently reuse this attestation as a permanently valid license.
    """
    def refuse(reason):
        raise PreopenError("CURRENT_MARKET_REUSE_BASIS_UNRESOLVED:" + reason)

    now = stamp(now) if isinstance(now, str) else now or datetime.now(JST)
    if (evidence.get("currentLegalReuseConfirmed") is not True
            or not evidence.get("authorizationReference")
            or not evidence.get("verifiedAt")):
        refuse("MISSING_POSITIVE_EVIDENCE")
    verified = stamp(evidence["verifiedAt"])
    if verified > now:
        refuse("FUTURE_CONFIRMATION")
    if evidence.get("verificationMethod") == "OWNER_CURRENT_WORK_CONTINUATION":
        # A later explicit acceptance of the concrete saved-original transfer
        # and research continuation is a new authorization event, not a new
        # subscription-renewal date. Keep the original renewal evidence intact.
        parent = evidence.get("priorRenewalEvidence")
        if (not isinstance(parent, dict)
                or parent.get("verificationMethod") != "OWNER_RENEWAL_ATTESTATION"
                or digest(parent) != evidence.get("priorRenewalEvidenceHash")
                or evidence.get("continuationScope") != "SAME_RESEARCH_SAVED_ORIGINAL_TRANSFER_AND_MEASUREMENT"
                or evidence.get("sourceKind") != "DIRECT_USER_MESSAGE"
                or not evidence.get("ownerStatement")
                or not evidence.get("acceptedPlanReference")
                or evidence.get("authorizationScope") != OWNER_SCOPE
                or evidence.get("attestationWorkId") != work_id
                or parent.get("attestationWorkId") != work_id
                or stamp(parent["verifiedAt"]) > verified):
            refuse("CONTINUATION_EVIDENCE_OR_SCOPE_MISMATCH")
        for key in ("contract", "ownerLogin", "connectedGithubLogin", "authorizationScope",
                    "repositories", "providerIndependentlyVerified", "providerExpiryVerified",
                    "validThrough", "newAcquisitionAuthorized", "publicRawUploadAllowed",
                    "sealedOutcomeReleaseAuthorized"):
            if evidence.get(key) != parent.get(key):
                refuse("CONTINUATION_SCOPE_EXPANDED")
        # Validate historical evidence at its real timestamp; the new event
        # itself must pass today's freshness check and the same work/safety gates.
        validate_reuse_authorization(parent, work_id=work_id, now=parent["verifiedAt"])
        if now - verified > ATTESTATION_FRESHNESS:
            refuse("CURRENT_WORK_CONTINUATION_STALE")
        require_safe_flags(evidence)
        return {"status": "OWNER_AUTHORIZED_CURRENT_WORK_CONTINUATION",
                "independentProviderVerification": False, "subscriptionExpiry": None,
                "attestationFreshnessGuardHours": 24,
                "authorizationReference": evidence["authorizationReference"],
                "originalRenewalVerifiedAt": parent["verifiedAt"],
                "continuationAuthorizedAt": evidence["verifiedAt"],
                "originalRenewalEvidenceHash": evidence["priorRenewalEvidenceHash"]}
    if evidence.get("verificationMethod") == "OWNER_RENEWAL_ATTESTATION":
        if (not work_id or evidence.get("attestationWorkId") != work_id
                or evidence.get("authorizationScope") != OWNER_SCOPE
                or evidence.get("contract") != CONTRACT
                or evidence.get("ownerLogin") != "Iam-2squared"
                or evidence.get("connectedGithubLogin") != "Iam-2squared"
                or evidence.get("sourceKind") != "DIRECT_USER_MESSAGE"
                or not evidence.get("ownerStatement")
                or not isinstance(evidence.get("repositories"), list)
                or set(evidence["repositories"]) != REPOSITORIES):
            refuse("OWNER_SCOPE_OR_WORK_ID_MISMATCH")
        if now - verified > ATTESTATION_FRESHNESS:
            refuse("CURRENT_WORK_ATTESTATION_STALE")
        if (evidence.get("providerIndependentlyVerified") is not False
                or evidence.get("providerExpiryVerified") is not False
                or evidence.get("validThrough") is not None
                or evidence.get("newAcquisitionAuthorized") is not False
                or evidence.get("publicRawUploadAllowed") is not False
                or evidence.get("sealedOutcomeReleaseAuthorized") is not False):
            refuse("ATTESTATION_MISCLASSIFIED_OR_SCOPE_EXPANDED")
        require_safe_flags(evidence)
        return {"status":"OWNER_ATTESTED_CURRENT_WORK_ONLY",
                "independentProviderVerification":False,
                "subscriptionExpiry":None,
                "attestationFreshnessGuardHours":24,
                "authorizationReference":evidence["authorizationReference"]}
    if not evidence.get("validThrough") or stamp(evidence["validThrough"]) < now:
        refuse("NO_CURRENT_VALIDITY_EVIDENCE")
    return {"status":"EVIDENCED_VALID_THROUGH",
            "authorizationReference":evidence["authorizationReference"],
            "validThrough":evidence["validThrough"]}
