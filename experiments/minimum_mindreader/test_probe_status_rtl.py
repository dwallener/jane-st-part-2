import shutil,subprocess,tempfile,unittest
from pathlib import Path
class Test(unittest.TestCase):
 def test_probe_status(self):
  i=shutil.which('iverilog');v=shutil.which('vvp');self.assertTrue(i and v);r=Path(__file__).resolve().parents[2]
  with tempfile.TemporaryDirectory() as d:
   o=Path(d)/'x';c=subprocess.run([i,'-g2012','-s','tb','-o',str(o),str(r/'src/active_probe_controller.v'),str(r/'src/mindreader_status.v'),str(r/'test/probe_status_tb.v')],capture_output=True,text=True);self.assertEqual(c.returncode,0,c.stderr);s=subprocess.run([v,str(o)],capture_output=True,text=True);self.assertEqual(s.returncode,0,s.stdout+s.stderr);self.assertIn('PROBE STATUS PASS',s.stdout)
