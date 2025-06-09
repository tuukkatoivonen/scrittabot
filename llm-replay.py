#!/usr/bin/env python3

import argparse
import json
import pprint
import requests
import urllib3
import yaml

parser = argparse.ArgumentParser()
parser.add_argument('--model', help='Override model to use')
parser.add_argument('--timeout', type=int, help='Set timeout', default=120)
args = parser.parse_args()

config = yaml.safe_load(open('config.yaml', 'r'))
payload = json.load(open('llm_exception_payload.json'))
timeout = args.timeout

if args.model:
    payload['model'] = args.model

url = config['openai_url'] + '/v1/chat/completions'
headers = { 'Content-Type': 'application/json' }
if 'openai_key' in config:
    headers['Authorization'] = f'Bearer {config["openai_key"]}'

urllib3.disable_warnings()  # Suppress all warnings from urllib3 (which requests uses)
print('----- Sending request ------')
response = requests.post(url, json=payload, headers=headers, timeout=timeout, verify=False)
print('----- Got request ------')
try:
    pprint.pp(response.json())
except:
    pprint.pp(response.text)
response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)
