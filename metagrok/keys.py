import json
import os

def get():
  try:
    with open(os.environ.get('METAGROK_KEYS_FILE', 'keys.json')) as fd:
      return json.load(fd)
  except:
    return None
