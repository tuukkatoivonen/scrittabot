#!/usr/bin/env python

# From:
# https://stackoverflow.com/questions/67431656/how-to-convert-json-to-yaml-and-vice-versa-in-command-line
# By: rzlvmp

import json,yaml,sys,os

if len(sys.argv) != 2:
  print('Usage:\n  '+os.path.basename(__file__)+' /path/file{.json|.yml}')
  sys.exit(0)

path = sys.argv[1]

if not os.path.isfile(path):
  print('Bad or non-existant file: '+path)
  sys.exit(1)

with open(path) as file:

  if path.lower().endswith('json'):
    print(yaml.dump(json.load(file), Dumper=yaml.CDumper))
  elif path.lower().endswith('yaml') or path.lower().endswith('yml'):
    print(json.dumps(yaml.load(file, Loader=yaml.SafeLoader), indent=2))
  else:
    print('Bad file extension. Must be yml or json')

