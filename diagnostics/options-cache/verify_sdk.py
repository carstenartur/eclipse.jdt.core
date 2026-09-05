#!/usr/bin/env python3
"""Verify the downloaded SDK against Eclipse's published SHA-512 manifest.

The manifest is retrieved from the official HTTPS drop directory. This is a
checksum comparison, not a claim that its detached GPG signature was verified.
"""
from pathlib import Path
import hashlib
import json
import re
import sys
from urllib.request import urlopen

base, archive_name, evidence_name = sys.argv[1:]
archive = Path(archive_name)
evidence = Path(evidence_name)
build = base.rstrip('/').rsplit('/', 1)[1]
filename = f'eclipse-SDK-{build}-linux-gtk-x86_64.tar.gz'
url = f'{base}/eclipse-{build}-checksums'
with urlopen(url, timeout=60) as response:
    manifest = response.read().decode('utf-8')
(evidence/'sdk-published-checksums.txt').write_text(manifest)
records = []
for line in manifest.splitlines():
    match = re.fullmatch(r'([0-9a-fA-F]{128})\s+\*?(?:\./)?' + re.escape(filename), line.strip())
    if match:
        records.append(match.group(1).lower())
if len(records) != 1:
    raise SystemExit(f'Expected one SHA-512 record for {filename} in {url}; found {len(records)}')
sha256 = hashlib.sha256()
sha512 = hashlib.sha512()
with archive.open('rb') as stream:
    for block in iter(lambda: stream.read(1024*1024), b''):
        sha256.update(block)
        sha512.update(block)
result = {'archive': filename, 'checksum_manifest_url': url,
          'sha256': sha256.hexdigest(), 'sha512': sha512.hexdigest(),
          'published_sha512': records[0], 'checksum_matches': sha512.hexdigest() == records[0]}
(evidence/'sdk-provenance.json').write_text(json.dumps(result, indent=2)+'\n')
print('SDK_PROVENANCE', json.dumps(result), flush=True)
if not result['checksum_matches']:
    raise SystemExit('Downloaded SDK does not match the official Eclipse checksum')
