#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

SETTINGS_PATH = '/a0/usr/settings.json'
ENV_CANDIDATES = [
    '/a0/.env',
    '/a0/usr/.env',
    '/root/.env',
    '/a0/usr/projects/private/.env',
]


def load_env_candidates():
    for p in ENV_CANDIDATES:
        path = Path(p)
        if not path.is_file():
            continue
        for raw in path.read_text(encoding='utf-8', errors='ignore').splitlines():
            line = raw.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())


def load_settings():
    with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def fetch_models(base_url: str, api_key: str):
    req = urllib.request.Request(
        base_url.rstrip('/') + '/models',
        headers={'Authorization': f'Bearer {api_key}'},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    return sorted({item.get('id') for item in data.get('data', []) if item.get('id')})


def main():
    parser = argparse.ArgumentParser(description='List LiteLLM models and mark current chat model.')
    parser.add_argument('--json', action='store_true', help='Emit JSON output')
    args = parser.parse_args()

    load_env_candidates()
    settings = load_settings()
    base_url = settings.get('chat_model_api_base', '').strip()
    current_model = settings.get('chat_model_name', '').strip()
    api_key = os.environ.get('API_KEY_OTHER', '').strip()

    if not base_url:
        raise SystemExit('chat_model_api_base missing in /a0/usr/settings.json')
    if not api_key:
        raise SystemExit('API_KEY_OTHER not found in environment or known .env files')

    models = fetch_models(base_url, api_key)
    if current_model in models:
        models = [m for m in models if m != current_model] + [current_model]

    if args.json:
        out = {
            'current_chat_model': current_model,
            'api_base': base_url,
            'models': [
                {
                    'id': m,
                    'current_chat_model': m == current_model,
                    'label': 'CURRENTLY USING FOR CHAT' if m == current_model else ''
                }
                for m in models
            ]
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    for m in models:
        if m == current_model:
            print(f'{m}\tCURRENTLY USING FOR CHAT')
        else:
            print(m)


if __name__ == '__main__':
    main()
