"""First and only B1/B2 Main invocation; immutable policy and replay engine."""
import control
control.COUNTS.update(primary_pP_diagnostic_solve=1,uniqueness_no_good_solve=1,independent_pP_diagnostic_solve=1)
import replay
if __name__=='__main__':replay.main()
