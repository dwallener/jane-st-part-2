import unittest
from known_protocol_corpus import DigitalWaveform,make_uart_case,make_i2c_write_case
from uart_inference import infer_uart
from i2c_inference import infer_i2c
class Test(unittest.TestCase):
 def test_uart(self):
  waves=tuple(make_uart_case(v).waveform for v in (0,0x55,0xa5,0xff));c=infer_uart(waves)
  exact=[x for x in c if (x.idle,x.bit_ticks,x.data_bits,x.parity,x.stop_bits)==(1,4,8,'none',1)]
  self.assertEqual(len(exact),1);self.assertEqual(exact[0].values,(0,0x55,0xa5,0xff));self.assertTrue(len(c)>=1)
  broken=list(make_uart_case(0x55).waveform.samples);broken[40:44]=[0]*4
  bad=infer_uart((DigitalWaveform(1,tuple(broken)),))
  self.assertFalse(any((x.idle,x.bit_ticks,x.data_bits,x.parity,x.stop_bits)==(1,4,8,'none',1) for x in bad))
 def test_i2c(self):
  c=infer_i2c(make_i2c_write_case().waveform);self.assertEqual(len(c),1);self.assertEqual((c[0].clock_pin,c[0].data_pin),(0,1));self.assertEqual(c[0].frames,(((0xa0,0x2a),(0,0)),));self.assertTrue(c[0].open_drain_required)
 def test_i2c_repeated_start(self):
  samples=[3];current=3
  def setpin(pin,value):
   nonlocal current
   current=(current|(1<<pin)) if value else (current&~(1<<pin));samples.append(current)
  def byte(value):
   for bit in range(7,-1,-1):setpin(0,0);setpin(1,(value>>bit)&1);setpin(0,1)
   setpin(0,0);setpin(1,0);setpin(0,1)
  setpin(1,0);byte(0xa0)
  setpin(0,0);setpin(1,1);setpin(0,1);setpin(1,0)
  byte(0xa1);byte(0x2a);setpin(0,0);setpin(1,0);setpin(0,1);setpin(1,1)
  candidates=infer_i2c(DigitalWaveform(2,tuple(samples)))
  self.assertEqual(len(candidates),1)
  self.assertEqual(candidates[0].frames,(((0xa0,),(0,)),((0xa1,0x2a),(0,0))))
