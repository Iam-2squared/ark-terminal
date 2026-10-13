import copy
import unittest
from preopen_io import SAFE_FLAGS
from preopen_reuse_authorization import validate_reuse_authorization, REPOSITORIES, OWNER_SCOPE
from preopen_selector import CONTRACT, PreopenError, digest


class OwnerContinuationTests(unittest.TestCase):
    def evidence(self):
        parent = {"currentLegalReuseConfirmed": True, "authorizationReference": "synthetic original message",
                  "verifiedAt": "2026-10-12T23:38:12+09:00", "verificationMethod": "OWNER_RENEWAL_ATTESTATION",
                  "attestationWorkId": "synthetic-work", "authorizationScope": OWNER_SCOPE,
                  "contract": CONTRACT, "ownerLogin": "Iam-2squared", "connectedGithubLogin": "Iam-2squared",
                  "sourceKind": "DIRECT_USER_MESSAGE", "ownerStatement": "synthetic renewal/use authorization",
                  "repositories": sorted(REPOSITORIES), "providerIndependentlyVerified": False,
                  "providerExpiryVerified": False, "validThrough": None, "newAcquisitionAuthorized": False,
                  "publicRawUploadAllowed": False, "sealedOutcomeReleaseAuthorized": False, **SAFE_FLAGS}
        return {**copy.deepcopy(parent), "verificationMethod": "OWNER_CURRENT_WORK_CONTINUATION",
                "verifiedAt": "2026-10-13T13:13:15+09:00", "authorizationReference": "synthetic later acceptance",
                "ownerStatement": "synthetic explicit acceptance", "acceptedPlanReference": "synthetic concrete plan",
                "continuationScope": "SAME_RESEARCH_SAVED_ORIGINAL_TRANSFER_AND_MEASUREMENT",
                "priorRenewalEvidence": parent, "priorRenewalEvidenceHash": digest(parent)}

    def test_new_event_keeps_original_timestamp_and_hash(self):
        evidence = self.evidence()
        before = copy.deepcopy(evidence)
        result = validate_reuse_authorization(evidence, work_id="synthetic-work", now="2026-10-14T00:20:00+09:00")
        self.assertEqual(result["originalRenewalVerifiedAt"], "2026-10-12T23:38:12+09:00")
        self.assertEqual(result["subscriptionExpiry"], None)
        self.assertEqual(evidence, before)

    def test_stale_continuation_and_future_event_rejected(self):
        for now in ("2026-10-14T13:13:16+09:00", "2026-10-13T13:13:14+09:00"):
            with self.assertRaises(PreopenError):
                validate_reuse_authorization(self.evidence(), work_id="synthetic-work", now=now)

    def test_parent_tampering_or_scope_expansion_rejected(self):
        for change in ("parent", "scope", "trading", "work"):
            e = self.evidence()
            if change == "parent": e["priorRenewalEvidence"]["verifiedAt"] = e["verifiedAt"]
            if change == "scope": e["newAcquisitionAuthorized"] = True
            if change == "trading": e["entryAllowed"] = True
            if change == "work": e["attestationWorkId"] = "another-work"
            with self.assertRaises(PreopenError):
                validate_reuse_authorization(e, work_id="synthetic-work", now="2026-10-14T00:20:00+09:00")

    def test_missing_concrete_plan_rejected(self):
        e = self.evidence(); e.pop("acceptedPlanReference")
        with self.assertRaises(PreopenError):
            validate_reuse_authorization(e, work_id="synthetic-work", now="2026-10-14T00:20:00+09:00")
