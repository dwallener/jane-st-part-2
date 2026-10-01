from dataclasses import dataclass
from itertools import permutations
from known_protocol_corpus import DigitalWaveform
@dataclass(frozen=True)
class I2cCandidate:
 clock_pin:int;data_pin:int;frames:tuple[tuple[tuple[int,...],tuple[int,...]],...];open_drain_required:bool=True
def decode(w,clock,data):
 frames=[];bits=[];active=False;prev=w.samples[0]
 if ((prev>>clock)&1)!=1 or ((prev>>data)&1)!=1:raise ValueError
 def finish(raw):
  groups=len(raw)//9
  if groups==0 or len(raw)-groups*9>=9:raise ValueError
  vals=[];acks=[]
  for g in range(groups):
   q=raw[g*9:g*9+9];v=0
   for b in q[:8]:v=(v<<1)|b
   vals.append(v);acks.append(q[8])
  return (tuple(vals),tuple(acks))
 for cur in w.samples[1:]:
  pc=(prev>>clock)&1;c=(cur>>clock)&1;pd=(prev>>data)&1;d=(cur>>data)&1
  if c and pd and not d:
   if active and bits:frames.append(finish(bits))
   active=True;bits=[]
  elif c and not pd and d:
   if not active:raise ValueError
   frames.append(finish(bits));active=False;bits=[]
  elif active and not pc and c:bits.append(d)
  prev=cur
 if active:raise ValueError
 return tuple(frames)
def infer_i2c(w):
 out=[]
 for clock,data in permutations(range(w.pin_count),2):
  try:frames=decode(w,clock,data)
  except ValueError:continue
  if frames:out.append(I2cCandidate(clock,data,frames))
 return tuple(out)
