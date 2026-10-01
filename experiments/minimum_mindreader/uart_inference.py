from dataclasses import dataclass
from known_protocol_corpus import DigitalWaveform
@dataclass(frozen=True)
class UartCandidate:
 idle:int;bit_ticks:int;data_bits:int;parity:str;stop_bits:int;values:tuple[int,...]
def _decode(w,idle,ticks,width,parity,stops):
 s=w.samples;start=next((i for i in range(1,len(s)) if (s[i-1]&1)==idle and (s[i]&1)!=idle),None)
 if start is None:return None
 symbols=1+width+(0 if parity=='none' else 1)+stops
 if start+symbols*ticks>len(s):return None
 levels=[]
 for n in range(symbols):
  chunk=s[start+n*ticks:start+(n+1)*ticks]
  if len(set(x&1 for x in chunk))!=1:return None
  levels.append(chunk[ticks//2]&1)
 if levels[0]==idle or any(x!=idle for x in levels[-stops:]):return None
 value=sum(levels[1+i]<<i for i in range(width))
 if parity!='none':
  p=levels[1+width];ones=value.bit_count()&1;expected=ones if parity=='even' else ones^1
  if p!=expected:return None
 return value
def infer_uart(waveforms):
 out=[]
 for idle in (0,1):
  for ticks in range(2,17):
   for width in range(5,10):
    for parity in ('none','even','odd'):
     for stops in (1,2):
      values=tuple(_decode(w,idle,ticks,width,parity,stops) for w in waveforms)
      if all(v is not None for v in values):out.append(UartCandidate(idle,ticks,width,parity,stops,values))
 return tuple(out)

def decode_uart_candidate(waveform,candidate):
 return _decode(waveform,candidate.idle,candidate.bit_ticks,candidate.data_bits,candidate.parity,candidate.stop_bits)
