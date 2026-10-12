import unittest
from scripts import phase57_saved_evidence_reuse as r


class ReuseTests(unittest.TestCase):
 def test_exact_existing_tree_is_reusable(self):
  self.assertEqual(r.unchanged({'scripts/model.py':'abc'},{'scripts/model.py':'abc'}),1)

 def test_research_code_change_is_blocked(self):
  with self.assertRaisesRegex(ValueError,'REUSE_BLOCKED'):
   r.unchanged({'scripts/model.py':'changed'},{'scripts/model.py':'original'})

 def test_artifact_change_is_blocked(self):
  with self.assertRaises(ValueError):
   r.unchanged({'docs/evidence/x/manifest.json':'changed'},{'docs/evidence/x/manifest.json':'original'})

 def test_deleted_or_missing_artifact_is_blocked(self):
  with self.assertRaises(ValueError):r.unchanged({}, {'docs/evidence/x/manifest.json':'original'})

 def test_new_unexecuted_files_do_not_invalidate_historical_research(self):
  self.assertEqual(r.unchanged({'scripts/model.py':'same','scripts/new.py':'new'},{'scripts/model.py':'same'}),1)

 def test_scope_contains_no_fit_measure_or_restore_commands(self):
  for _, command, _ in r.STUDIES.values():
   self.assertNotIn('measure',command);self.assertNotIn('fit',command);self.assertNotIn('restore',command)

 def test_freeze_qualification_is_not_overridden(self):
  self.assertFalse(any('freeze' in x for x in r.STUDIES))


if __name__ == '__main__':unittest.main()
