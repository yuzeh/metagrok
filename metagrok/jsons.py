from metagrok import np_json as json
from metagrok.fileio import to_fd

def load(fd_or_name):
  return list(stream(fd_or_name))

def stream(fd_or_name):
  with to_fd(fd_or_name) as fd:
    for line in fd:
      yield json.loads(line.strip())

def dump(fd_or_name, itr, dumps = json.dumps):
  with to_fd(fd_or_name, 'w') as fd:
    for obj in itr:
      json_str = dumps(obj)
      fd.write(json_str)
      fd.write('\n')
