# North-Star audit: incidental CI replay disclosure

This is an execution-boundary incident, not a new research result. The user required
no refitting or Entry/EXIT/Allocation research during the North-Star measurement
audit. The initial contract commit unintentionally triggered pre-existing
`pull_request.paths` workflows: their filters considered the complete PR diff,
not merely the latest commit. This was not checked adequately before the push.

Consequently, a blanket statement that **no refit ran anywhere during this task
would be false**. The dedicated measurement run itself performs no fit, no provider
acquisition, and consumes only its predeclared historical artifacts. Incidental
outputs were not consumed or used to choose tests, weights, thresholds or policies.

## Verified terminal states

| Trigger commit | Run | Terminal status | Verified stage |
|---|---|---|---|
| Contract `9acfd892` | [34975517664](https://github.com/Iam-2squared/ark-terminal/actions/runs/34975517664) | SUCCESS | Existing Capacity script completed C-only refit/hash verification and diagnostic |
| Contract | [34975517535](https://github.com/Iam-2squared/ark-terminal/actions/runs/34975517535) | SUCCESS | Existing Missed script completed C-only refit/hash verification and diagnostic |
| Contract | [34975517579](https://github.com/Iam-2squared/ark-terminal/actions/runs/34975517579) | SUCCESS | Existing L2 ablation, selection and final refit completed before cancellation arrived |
| Contract | [34975517538](https://github.com/Iam-2squared/ark-terminal/actions/runs/34975517538) | CANCELLED | Ridge fit and ranking completed; exact subsequent Entry/EXIT stage is not observable from available progress logs |
| Diagnostic code `d7d6cb8e` | [34976219728](https://github.com/Iam-2squared/ark-terminal/actions/runs/34976219728) | CANCELLED | Preparation stopped after C20+D12; before real-data fit |
| Diagnostic code | [34976219787](https://github.com/Iam-2squared/ark-terminal/actions/runs/34976219787) | CANCELLED | Preparation stopped after C20+D1; before fit |
| Diagnostic code | [34976219838](https://github.com/Iam-2squared/ark-terminal/actions/runs/34976219838) | CANCELLED | Preparation stopped after C20+D1; before fit |
| Diagnostic code | [34976219852](https://github.com/Iam-2squared/ark-terminal/actions/runs/34976219852) | CANCELLED | Preparation stopped after C20; before fit |

Completed L2 replay reproduced the pre-existing freeze SHA
`e883168e49b0ee2cf75e4b5bb1053c170b1ca58621a50ff004cd0aa973bfdf15`.
No incidental artifact is an input to the new measurement run. The cancelled
integration run did not upload a final comparison report. Its last progress line
was replay-bar preparation completion at 13:41:48 UTC, and cancellation completed
at 13:43:59 UTC. Entry training/fit/replay have no intermediate progress markers;
therefore their precise stopping point cannot be asserted. Cleanup succeeded.

## Containment

- [Guard commit 28c9bf0](https://github.com/Iam-2squared/ark-terminal/commit/28c9bf0f3cb0d3e96aa1c94aff9baaea2b3371a4)
  limits the four old research jobs to explicit manual dispatch. Their new PR jobs
  were verified skipped. Research model/entry/exit/allocation source code was not edited.
- Existing scoped cancellation workflow was updated with exact resolved run IDs;
  cancellation runs [34976367659](https://github.com/Iam-2squared/ark-terminal/actions/runs/34976367659)
  and [34976788379](https://github.com/Iam-2squared/ark-terminal/actions/runs/34976788379)
  succeeded. Completed replays could not be undone and were not deleted or hidden.
- [Dedicated North-Star run 34976208234](https://github.com/Iam-2squared/ark-terminal/actions/runs/34976208234)
  was preserved. Its own no-fit safety flags describe that run, not every incidental
  GitHub workflow triggered during the task.
- No model artifact was promoted, no live-circuit/main/Lane Y code was changed,
  no new model/target/feature/policy was adopted, and no live orders were submitted.

The final report must retain this distinction. The no-refit execution constraint
was not fully respected at the surrounding CI level, despite the dedicated audit
being evaluator-only.
