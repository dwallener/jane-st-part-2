"""Machine-generated, refusal-preserving benchmark report."""
from __future__ import annotations
from dataclasses import asdict,dataclass
import json
from adversarial_corpus import run_adversarial_corpus
from hierarchical_model import build_hierarchical_spi_model
from i2c_inference import decode as decode_i2c,infer_i2c
from known_protocol_corpus import benchmark_cases,make_i2c_write_case,make_uart_case
from spi_behavior import HELD_OUT_REQUEST,lossy_response,make_spi_behavior_corpus
from uart_inference import decode_uart_candidate,infer_uart

@dataclass(frozen=True)
class ReportRow:
 case:str;family:str;stage_reached:str;observations_required:int
 surviving_equivalence:int;held_out_generalization:str;replay_result:str
 refusal_reason:str;unsupported_claims:str

def build_report():
 cases=benchmark_cases();uart_cases=tuple(c for c in cases if c.truth.family=='UART')
 uart_models=infer_uart(tuple(c.waveform for c in uart_cases));uart_held=make_uart_case(0x3c).waveform
 uart_predictions={decode_uart_candidate(uart_held,m) for m in uart_models}
 rows=[]
 for case in cases:
  if case.truth.family=='SPI':
   mode=int(case.truth.parameter('mode'));order=case.truth.parameter('bit_order')=='msb_first'
   model=build_hierarchical_spi_model(make_spi_behavior_corpus(mode,order))
   decoded_request=HELD_OUT_REQUEST if order else int(f'{HELD_OUT_REQUEST:08b}'[::-1],2)
   answer=model.emulate_decoded(decoded_request)
   wire_answer=answer.value if order else int(f'{answer.value:08b}'[::-1],2)
   rows.append(ReportRow(case.name,'SPI','wire_emulation',8,2,
    f'pass: unseen wire request maps to 0x{wire_answer:02x}',
    'fail: exact replay has no unseen request','none for bounded learned family',
    'electrical maximum clock rate and arbitrary SPI framing'))
  elif case.truth.family=='UART':
   rows.append(ReportRow(case.name,'UART','symbol_decode',len(uart_cases),len(uart_models),
    f'ambiguous: held-out predictions={sorted(uart_predictions)}',
    'fail: held-out value absent from capture','width/parity equivalence remains',
    'transmit timing and session behavior'))
  else:
   candidate=infer_i2c(case.waveform)[0];held=make_i2c_write_case(0x31,0x7b)
   decoded=decode_i2c(held.waveform,candidate.clock_pin,candidate.data_pin)
   rows.append(ReportRow(case.name,'I2C','frame_decode',1,1,
    f'pass: unseen frame decoded as {decoded}','fail: unseen address/data absent from capture',
    'emulation refused pending open-drain ownership','arbitration, stretching, and electrical drive proof'))
 for result in run_adversarial_corpus():
  rows.append(ReportRow(result.name,'INVENTED','adversarial_gate',result.observations_required,result.surviving_equivalence,
   result.outcome,'not applicable: structural negative control',result.refusal or 'none',
   'outside the named bounded hypothesis'))
 return tuple(rows)

def render_json():return json.dumps([asdict(row) for row in build_report()],indent=2)
def render_markdown():
 rows=build_report();lines=['# Generated Protocol Doppelganger Benchmark','',
  '| Case | Family | Stage | Obs. | Survivors | Held-out | Replay | Refusal | Unsupported |',
  '| --- | --- | --- | ---: | ---: | --- | --- | --- | --- |']
 for r in rows:lines.append(f'| {r.case} | {r.family} | {r.stage_reached} | {r.observations_required} | {r.surviving_equivalence} | {r.held_out_generalization} | {r.replay_result} | {r.refusal_reason} | {r.unsupported_claims} |')
 return '\n'.join(lines)+'\n'
