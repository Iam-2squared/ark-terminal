export const P25_RESEARCH_COST_POLICY_VERSION = 'p25-research-cost-policy-v1';

// Research assumptions only. This is not a broker fee schedule and must not be
// tuned from observed P25 performance. The zero-cost path remains available only
// for plumbing/debug comparisons; the predeclared baseline uses 10 bps adverse
// slippage per simulated fill.
export const P25_RESEARCH_COST_POLICY_V1 = Object.freeze({
  version: P25_RESEARCH_COST_POLICY_VERSION,
  id: 'PREDECLARED_2026_08_23_V1',
  currency: 'JPY',
  commissionPerFill: 0,
  slippageBps: 10,
  sensitivitySlippageBps: Object.freeze([0, 5, 10, 20]),
  brokerTariffClaimed: false,
  tunedFromProspectivePerformance: false,
  effectiveForNewResearchPaperSessionsOnly: true,
  executable: false,
});

export function validateP25ResearchCostPolicy(policy = P25_RESEARCH_COST_POLICY_V1) {
  if (!policy || policy.version !== P25_RESEARCH_COST_POLICY_VERSION) throw new Error('invalid P25 research cost policy version');
  if (!Number.isFinite(Number(policy.commissionPerFill)) || Number(policy.commissionPerFill) < 0) throw new Error('commissionPerFill must be non-negative');
  if (!Number.isFinite(Number(policy.slippageBps)) || Number(policy.slippageBps) < 0) throw new Error('slippageBps must be non-negative');
  if (!Array.isArray(policy.sensitivitySlippageBps) || policy.sensitivitySlippageBps.length === 0) throw new Error('sensitivitySlippageBps required');
  for (const value of policy.sensitivitySlippageBps) if (!Number.isFinite(Number(value)) || Number(value) < 0) throw new Error('invalid sensitivity slippage');
  if (policy.brokerTariffClaimed !== false) throw new Error('research policy must not claim broker tariff equivalence');
  if (policy.tunedFromProspectivePerformance !== false) throw new Error('research cost policy must be predeclared');
  if (policy.executable !== false) throw new Error('research cost policy must remain non-executable');
  return true;
}
