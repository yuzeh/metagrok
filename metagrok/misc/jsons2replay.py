import argparse
import codecs
import os
import sys

from metagrok import jsons
from metagrok import config
from metagrok import torch_policy

sys.stdout = codecs.getwriter('utf8')(sys.stdout)

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('in_file')
  parser.add_argument('specs', nargs = '*')
  parser.add_argument('--show-default', action = 'store_true')
  args = parser.parse_args()

  config.set_cuda(False)

  policies = []
  for t in args.specs:
    name = os.path.splitext(os.path.basename(t.split(':')[-1]))[0]
    policy = torch_policy.load(t)
    policies.append((name, policy))

  lines = []
  switch = 'false'
  found = False
  for line in jsons.stream(args.in_file):
    if len(lines) == 0:
      whoami = line['state']['whoami']
    for update in line['_updates']:
      if update.startswith('|error') or update.startswith('|request'):
        continue
      update = update.strip()
      if update.startswith('|player'):
        _1, _2, pid, pname = update.split('|')[:4]
        if pname == whoami:
          assert not found
          found = True
          switch = 'true' if pid == 'p2' else 'false'
      lines.append(update.strip())
    if 'candidates' in line:
      lines.append(make_table(line, policies, args.show_default))
  assert found

  lines = '\n'.join(lines)
  print(TEMPLATE % (lines, switch))

def make_table(line, policies, show_default):
  candidates = line['candidates']
  state = line['state']
  fmt = '%.4f'
  header = ['model'] + candidates + ['value_pred']
  rows = [header]

  if show_default:
    rows.append(['default'] + list(fmt % p for p in line['probs']) + [fmt % line['value_pred']])

  for name, policy in policies:
    row = [name]
    result = policy.act(state, candidates)
    row.extend(fmt % p for p in result['probs'])
    row.append(fmt % result['value_pred'])
    rows.append(row)

  rows = [
      [el for el, head in zip(els, header) if head]
      for els in rows
  ]

  head = '<thead>{head}</thead>'.format(head = mk_row(rows[0], is_header = True))
  bodies = [mk_row(r) for r in rows[1:]]
  body = '<tbody>' + ''.join(bodies) + '</tbody>'

  return '|raw|' + ''.join(['<table border="1">', head, body, '</table>'])

def mk_row(es, is_header = False):
  if is_header:
    tag = 'th'
  else:
    tag = 'td'
  middle = ''.join('<{tag} width="100px">{name}'.format(tag = tag, name = e) for e in es)
  return '<tr>' + middle + '</tr>'

TEMPLATE = '''
<!DOCTYPE html>
<meta charset="utf-8" />
<!-- version 1 -->
<title>Replay</title>
<style>
html,body {
  font-family:Verdana, sans-serif;
  font-size:10pt;
  margin:0;
  padding:0;
}
body{
  padding:12px 0;
}
.battle {
  left: 25%% !important;
}
.battle-log {
  font-family:Verdana, sans-serif;
  font-size:10pt;
  position: static !important;
  height: 300px !important;
}
.battle-log-inline {
  border:1px solid #AAAAAA;background:#EEF2F5;
  color:black;
  max-width:640px;
  margin:0 auto 80px;
  padding-bottom:5px;
}
.battle-log .inner {padding:4px 8px 0px 8px;}
.battle-log .inner-preempt {padding:0 8px 4px 8px;}
.battle-log .inner-after {margin-top:0.5em;}
.battle-log h2 {
  margin:0.5em -8px;
  padding:4px 8px;
  border:1px solid #AAAAAA;
  background:#E0E7EA;
  border-left:0;
  border-right:0;
  font-family:Verdana, sans-serif;
  font-size:13pt;
}
.battle-log .chat {vertical-align:middle;padding:3px 0 3px 0;font-size:8pt;}
.battle-log .chat strong {color:#40576A;}
.battle-log .chat em {padding:1px 4px 1px 3px;color:#000000;font-style:normal;}
.chat.mine {background:rgba(0,0,0,0.05);margin-left:-8px;margin-right:-8px;padding-left:8px;padding-right:8px;}
.spoiler {color:#BBBBBB;background:#BBBBBB;padding:0px 3px;}
.spoiler:hover, .spoiler:active, .spoiler-shown {color:#000000;background:#E2E2E2;padding:0px 3px;}
.spoiler a {color:#BBBBBB;}
.spoiler:hover a, .spoiler:active a, .spoiler-shown a {color:#2288CC;}
.chat code, .chat .spoiler:hover code, .chat .spoiler:active code, .chat .spoiler-shown code {border:1px solid #C0C0C0;background:#EEEEEE;color:black;padding:0 2px;}
.chat .spoiler code {border:1px solid #CCCCCC;background:#CCCCCC;color:#CCCCCC;}
.battle-log .rated {padding:3px 4px;}
.battle-log .rated strong {color:white;background:#89A;padding:1px 4px;border-radius:4px;}
.spacer {margin-top:0.5em;}
.message-announce {background:#6688AA;color:white;padding:1px 4px 2px;}
.message-announce a, .broadcast-green a, .broadcast-blue a, .broadcast-red a {color:#DDEEFF;}
.broadcast-green {background-color:#559955;color:white;padding:2px 4px;}
.broadcast-blue {background-color:#6688AA;color:white;padding:2px 4px;}
.infobox {border:1px solid #6688AA;padding:2px 4px;}
.infobox-limited {max-height:200px;overflow:auto;overflow-x:hidden;}
.broadcast-red {background-color:#AA5544;color:white;padding:2px 4px;}
.message-learn-canlearn {font-weight:bold;color:#228822;text-decoration:underline;}
.message-learn-cannotlearn {font-weight:bold;color:#CC2222;text-decoration:underline;}
.message-effect-weak {font-weight:bold;color:#CC2222;}
.message-effect-resist {font-weight:bold;color:#6688AA;}
.message-effect-immune {font-weight:bold;color:#666666;}
.message-learn-list {margin-top:0;margin-bottom:0;}
.message-throttle-notice, .message-error {color:#992222;}
.message-overflow, .chat small.message-overflow {font-size:0pt;}
.message-overflow::before {font-size:9pt;content:'...';}
.subtle {color:#3A4A66;}
</style>
<div class="wrapper replay-wrapper" style="max-width:1180px;margin:0 auto">
  <input type="hidden" name="replayid" value="32" />
  <div class="battle"></div>
  <div class="battle-log"></div>
  <div class="replay-controls"></div><div class="replay-controls-2"></div>
    <script type="text/plain" class="battle-log-data">%s</script>
  </div>
</div>
<script>
var date = Date.now();
//var date = new Date('2018-01-01');
var daily = Math.floor(date/1000/60/60/24);document.write('<script src="https://play.pokemonshowdown.com/js/replay-embed.js?version'+daily+'"></' + 'script>');
</script>
<script>
var oldReplayStart = Replays.start.bind(Replays);
Replays.start = function () {
  oldReplayStart();
  if (%s) {
    this.battle.switchSides();
  }
};
</script>
'''

if __name__ == '__main__':
  main()
