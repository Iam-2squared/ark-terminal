"""Independent certification of the preserved original failed solve."""
from common import *
from independent_solver import certify
def main():
 r=json.loads((PRIVATE/'BLOCK07_NUMERIC_ISOLATION.json').read_text());a=r['candidate_physical_continuation'];h=r['held_release_obligations'];state=r['state'];x=r['solver_results'][-1]['x']
 cert=certify(state,a,h,True,[round(v) for v in x]);out={'exact_jst':now(),'state_key':state['state_key'],'original_reported_gap':r['solver_results'][-1]['mip_gap'],'original_turnover_incumbent_minus_dual_jpy':(r['solver_results'][-1]['fun']-r['solver_results'][-1]['mip_dual_bound'])*1e6,'independent_certificate':cert,'problem_or_objective_or_threshold_changed':False,'result_retune':0,'slot_fit':0,'main_replay':0}
 save(OUT/'BLOCK07_INDEPENDENT_NUMERIC_CERTIFICATE.json',out);print(json.dumps(out))
if __name__=='__main__':main()
