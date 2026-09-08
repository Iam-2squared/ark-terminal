import {loadCheckpoints,auditRows,writeReport} from './capacity_v22_checkpoint.mjs';
const {rows,ancestry}=loadCheckpoints();
const report={...auditRows(rows),ancestry};
writeReport('artifacts/capacity-v22-semantics','audit.json',report);
console.log('V22_AUDIT_JSON '+JSON.stringify(report));
