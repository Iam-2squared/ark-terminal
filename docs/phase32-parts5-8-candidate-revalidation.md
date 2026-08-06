# Phase32 Parts5-8: Candidate Specification and Revalidation

## Scope

- Part5: convert reviewed improvement proposals into immutable candidate specifications
- Part6: build a strict Phase31 revalidation plan
- Part7: aggregate Candidate/Champion review results for the dashboard
- Part8: require explicit human review before manual Candidate registration

## Safety contract

This phase does not create or promote a model automatically.

- automaticCandidateCreationAllowed: false
- automaticPromotionAllowed: false
- productionUpdateAllowed: false
- brokerWriteAllowed: false
- liveTradingAllowed: false
- orderCreationAllowed: false
- orderTransmissionAllowed: false
- orderCancellationAllowed: false
- orderModificationAllowed: false
- excelOrderWriteAllowed: false
- orderTriggerWriteAllowed: false
- humanApprovalRequired: true

The highest successful state is `APPROVED_FOR_MANUAL_CANDIDATE_REGISTRATION`.
This means a human may register a Candidate for further paper/forward validation. It never means automatic promotion or Production deployment.
