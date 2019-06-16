import sys

DTYPE = 'float32'
ENCODING = (getattr(sys.stdin, 'encoding', 'utf-8') or 'utf-8').lower()
LOG_FORMAT = '%(asctime)s ~ %(name)s ~ %(levelname)-8.8s ~ %(message)s'
