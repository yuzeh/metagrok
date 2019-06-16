import json
import os

def get():
  with open(os.environ.get('METAGROK_KEYS_FILE', 'keys.json')) as fd:
    return json.load(fd)
