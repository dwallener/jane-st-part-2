import shutil,subprocess,tempfile,unittest
from pathlib import Path
class Test(unittest.TestCase):
 def test_boundary(self):
  iv=shutil.which('iverilog');vv=shutil.which('vvp');self.assertTrue(iv and vv);r=Path(__file__).resolve().parents[2]
  with tempfile.TemporaryDirectory() as d:
   o=Path(d)/'x';c=subprocess.run([iv,'-g2012','-s','tb','-o',str(o),str(r/'src/spi_transaction_decoder.v'),str(r/'src/spi_timing_guard.v'),str(r/'src/pin_contention_monitor.v'),str(r/'test/spi_boundary_tb.v')],capture_output=True,text=True);self.assertEqual(c.returncode,0,c.stderr)
   s=subprocess.run([vv,str(o)],capture_output=True,text=True);self.assertEqual(s.returncode,0,s.stdout+s.stderr);self.assertIn('SPI BOUNDARY PASS',s.stdout)
