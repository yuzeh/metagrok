import csv

def main():
  args = parse_args()
  for row in csv.DictReader(args.csv_inp):
    white = row['white']
    black = row['black']
    w_num = int(row['wins'])
    l_num = int(row['losses'])

    for _ in xrange(w_num):
      args.pgn_out.write('[White "%s"][Black "%s"][Result "1-0"] 1. c4 Nf6\n' % (white, black))
    for _ in xrange(l_num):
      args.pgn_out.write('[White "%s"][Black "%s"][Result "0-1"] 1. c4 Nf6\n' % (white, black))

def parse_args():
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('csv_inp', type = argparse.FileType('r'))
  parser.add_argument('pgn_out', type = argparse.FileType('w'))
  return parser.parse_args()

if __name__ == '__main__':
  main()
