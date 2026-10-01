import unittest
from benchmark_report import build_report,render_json,render_markdown
class Test(unittest.TestCase):
 def test_report_is_complete_and_refusal_preserving(self):
  rows=build_report();self.assertEqual(len(rows),19)
  self.assertTrue(all(r.case and r.family and r.stage_reached and r.observations_required>0 and r.surviving_equivalence>=0 and r.held_out_generalization and r.replay_result and r.refusal_reason and r.unsupported_claims for r in rows))
  self.assertEqual(sum(r.family=='SPI' for r in rows),8);self.assertEqual(sum(r.family=='UART' for r in rows),4);self.assertEqual(sum(r.family=='I2C' for r in rows),1);self.assertEqual(sum(r.family=='INVENTED' for r in rows),6)
  self.assertTrue(all('exact replay' in r.replay_result for r in rows if r.family=='SPI'))
  self.assertTrue(all(r.held_out_generalization.startswith('ambiguous') for r in rows if r.family=='UART'))
  self.assertIn('open-drain',next(r.refusal_reason for r in rows if r.family=='I2C'))
 def test_both_serializations_name_every_case(self):
  for row in build_report():self.assertIn(row.case,render_markdown());self.assertIn(row.case,render_json())
