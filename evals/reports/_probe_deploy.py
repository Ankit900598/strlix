import json, subprocess, urllib.request, urllib.error

def deploy(name, body):
    token = subprocess.check_output([
      r'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd', 'account', 'get-access-token',
      '--resource', 'https://management.azure.com/', '-o', 'tsv', '--query', 'accessToken'
    ], text=True).strip()
    url = f'https://management.azure.com/subscriptions/a3dc5296-f948-427e-8656-c6bc52afee21/resourceGroups/phonecodex-dev/providers/Microsoft.CognitiveServices/accounts/ay186mnc-1561-resource/deployments/{name}?api-version=2025-10-01-preview'
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method='PUT', headers={
      'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'
    })
    try:
      with urllib.request.urlopen(req, timeout=120) as r:
        return 'OK', r.read().decode()[:500]
    except urllib.error.HTTPError as e:
      return f'ERR {e.code}', e.read().decode()[:500]

probes = [
  ('pc-lab-reasoning', {'sku': {'name': 'GlobalStandard', 'capacity': 1}, 'properties': {'model': {'format': 'OpenAI', 'name': 'gpt-5.4', 'version': '2026-03-05'}}}),
  ('pc-lab-premium', {'sku': {'name': 'GlobalStandard', 'capacity': 1}, 'properties': {'model': {'format': 'OpenAI', 'name': 'gpt-6-astra', 'version': '2026-09-03'}}}),
  ('pc-lab-fallback', {'sku': {'name': 'Standard', 'capacity': 1}, 'properties': {'model': {'format': 'OpenAI', 'name': 'gpt-5.1', 'version': '2025-11-13'}}}),
]
for name, body in probes:
    s, m = deploy(name, body)
    print(name, body['properties']['model']['name'], s)
    print(m)
    print()
