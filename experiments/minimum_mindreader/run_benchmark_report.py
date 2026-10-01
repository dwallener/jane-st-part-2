import argparse
from benchmark_report import render_json,render_markdown
p=argparse.ArgumentParser();p.add_argument('--json',action='store_true');a=p.parse_args()
print(render_json() if a.json else render_markdown(),end='')
