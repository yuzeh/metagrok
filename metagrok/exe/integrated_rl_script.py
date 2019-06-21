import multiprocessing as mp
import shutil
import subprocess
import sys

from metagrok import utils
from metagrok import np_json as json
from metagrok import integrated_rl

def main():
  args = parse_args()

  logger = utils.default_logger_setup()

  utils.mkdir_p(args.base_dir)
  expt = json.load(args.expt_name)

  last_iter = None
  while True:
    current_iter = integrated_rl.divine_current_iteration(args.base_dir)
    logger.info('Current iteration: %d', current_iter)

    if last_iter is not None:
      if last_iter >= current_iter:
        raise ValueError(
          'No progress made. last_iter = %s, current_iter = %s' % (last_iter, current_iter))
    last_iter = current_iter

    if current_iter >= expt['num_iters']:
      break
    cmd = ['./rp', 'metagrok/integrated_rl.py']
    cmd.extend(sys.argv[1:])
    logger.info('Running command: %s', cmd)
    subprocess.check_call(cmd, stdout = sys.stdout, stderr = sys.stderr)

    logger.info('Evicting /tmp directory')
    shutil.rmtree('/tmp')
    utils.mkdir_p('/tmp')

  logger.info('Done!')

def parse_args():
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('expt_name')
  parser.add_argument('base_dir')
  parser.add_argument('--cuda', action = 'store_true')
  parser.add_argument('--parallelism', type = int, default = mp.cpu_count())

  return parser.parse_args()

if __name__ == '__main__':
  main()