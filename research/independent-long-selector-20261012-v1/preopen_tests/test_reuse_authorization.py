"""Authority classification tests; no market data and no estimator fit."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from preopen_io import SAFE_FLAGS, write_json
from preopen_reuse_authorization import (
    OWNER_SCOPE, REPOSITORIES, validate_reuse_authorization)
from preopen_selector import CONTRACT, PreopenError, stamp
from preopen_native_source import validate_native_request
from test_native_completion import fixture


def owner_evidence():
    return {"currentLegalReuseConfirmed":True,
            "authorizationReference":"SYNTHETIC_DIRECT_OWNER_ATTESTATION",
            "verifiedAt":"2026-10-12T23:38:12+09:00",
            "verificationMethod":"OWNER_RENEWAL_ATTESTATION",
            "attestationWorkId":"synthetic-work-id",
            "authorizationScope":OWNER_SCOPE,"contract":CONTRACT,
            "ownerLogin":"Iam-2squared","connectedGithubLogin":"Iam-2squared",
            "sourceKind":"DIRECT_USER_MESSAGE","ownerStatement":"SYNTHETIC_RENEWAL",
            "repositories":sorted(REPOSITORIES),
            "providerIndependentlyVerified":False,"providerExpiryVerified":False,
            "validThrough":None,"newAcquisitionAuthorized":False,
            "publicRawUploadAllowed":False,"sealedOutcomeReleaseAuthorized":False,
            **SAFE_FLAGS}


class ReuseAuthorizationTests(unittest.TestCase):
    def check(self, evidence, **kw):
        return validate_reuse_authorization(
            evidence, work_id=kw.get("work_id", "synthetic-work-id"),
            now=kw.get("now", "2026-10-12T23:40:00+09:00"))

    def test_owner_attestation_has_no_invented_provider_expiry(self):
        result = self.check(owner_evidence())
        self.assertEqual(result["status"], "OWNER_ATTESTED_CURRENT_WORK_ONLY")
        self.assertIsNone(result["subscriptionExpiry"])
        self.assertIs(result["independentProviderVerification"], False)

    def test_false_confirmation_and_reference_absence_fail_closed(self):
        for field, value in (("currentLegalReuseConfirmed", False),
                             ("authorizationReference", ""), ("verifiedAt", "")):
            with self.subTest(field=field):
                evidence=owner_evidence(); evidence[field]=value
                with self.assertRaisesRegex(PreopenError, "REUSE_BASIS"):
                    self.check(evidence)

    def test_attestation_is_bound_to_current_work_and_repository_owner(self):
        for field, value in (("attestationWorkId", "other-work"),
                             ("ownerLogin", "other-owner"),
                             ("connectedGithubLogin", "other-owner"),
                             ("authorizationScope", "PERMANENT_ALL_PROJECTS"),
                             ("repositories", ["Iam-2squared/ark-ai"])):
            with self.subTest(field=field):
                evidence=owner_evidence(); evidence[field]=value
                with self.assertRaisesRegex(PreopenError, "SCOPE_OR_WORK_ID"):
                    self.check(evidence)
        with self.assertRaisesRegex(PreopenError, "SCOPE_OR_WORK_ID"):
            self.check(owner_evidence(), work_id=None)

    def test_exact_freshness_boundary_and_future_confirmation(self):
        self.check(owner_evidence(), now="2026-10-13T23:38:12+09:00")
        with self.assertRaisesRegex(PreopenError, "STALE"):
            self.check(owner_evidence(), now="2026-10-13T23:38:12.000001+09:00")
        with self.assertRaisesRegex(PreopenError, "FUTURE"):
            self.check(owner_evidence(), now="2026-10-12T23:38:11+09:00")

    def test_scope_expansion_and_false_independent_verification_rejected(self):
        for field, value in (("providerIndependentlyVerified", True),
                             ("providerExpiryVerified", True),
                             ("validThrough", "2027-10-12T23:38:12+09:00"),
                             ("newAcquisitionAuthorized", True),
                             ("publicRawUploadAllowed", True),
                             ("sealedOutcomeReleaseAuthorized", True)):
            with self.subTest(field=field):
                evidence=owner_evidence(); evidence[field]=value
                with self.assertRaisesRegex(PreopenError, "SCOPE_EXPANDED"):
                    self.check(evidence)

    def test_execution_flags_remain_false(self):
        for flag in SAFE_FLAGS:
            with self.subTest(flag=flag):
                evidence=owner_evidence(); evidence[flag]=True
                with self.assertRaisesRegex(PreopenError, "UNSAFE_OR_MISSING_FLAG"):
                    self.check(evidence)

    def test_previous_explicit_validity_path_is_preserved(self):
        evidence={"currentLegalReuseConfirmed":True,
                  "authorizationReference":"SYNTHETIC_PROVIDER_RECORD",
                  "verifiedAt":"2026-10-06T16:00:00+09:00",
                  "validThrough":"2026-10-13T00:00:00+09:00"}
        self.assertEqual(self.check(evidence)["status"], "EVIDENCED_VALID_THROUGH")
        evidence["validThrough"]=None
        with self.assertRaisesRegex(PreopenError, "NO_CURRENT_VALIDITY"):
            self.check(evidence)

    def test_owner_renewal_does_not_release_other_native_preflight_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); request=fixture(root)
            request.update(mode="AUTHORIZED_DEVELOPMENT",reuseWorkId="synthetic-work-id",
                           historicalSourceAssumptionsReviewed=False)
            request["currentReuseEvidence"]=write_json(root/"renewal.json",owner_evidence())
            with patch("preopen_reuse_authorization.datetime") as clock:
                clock.now.return_value=stamp("2026-10-12T23:40:00+09:00")
                with self.assertRaisesRegex(PreopenError, "ASSUMPTIONS_UNREVIEWED"):
                    validate_native_request(request,root)


if __name__ == "__main__":
    unittest.main()
