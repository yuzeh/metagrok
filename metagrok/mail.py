import os

import requests

from metagrok import keys

import logging

logger = logging.getLogger(__name__)

_keys = keys.get()

def send(subject, text, attachments = []):
  if _keys is None:
    logger.warn('Not sending out email, metagrok.keys module is not set up properly')
    return None

  files = []
  for a in attachments:
    files.append(('attachment', (a, open(a, 'rb'), 'text/plain')))

  rv = requests.post(
      'https://api.mailgun.net/v3/%s/messages' % _keys['mailgun_domain'],
      auth = ('api', _keys['mailgun_api_key']),
      data = {
        'from': _keys['mailgun_sender'],
        'to': [_keys['mailgun_recipient']],
        'subject': subject,
        'text': text,
      },
      files = files,
  )

  for _, (_, fd, _) in files:
    fd.close()
  return rv
