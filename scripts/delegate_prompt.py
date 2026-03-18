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


def build_messages(system_prompt: str, user_prompt: str, messages_file: str | None):
    messages = []
    if messages_file:
        with open(messages_file, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        if not isinstance(loaded, list):
            raise SystemExit('messages file must contain a JSON list of messages')
        messages.extend(loaded)
    else:
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        if user_prompt:
            messages.append({'role': 'user', 'content': user_prompt})
    if not messages:
        raise SystemExit('No messages to send')
    return messages


def post_chat(base_url: str, api_key: str, payload: dict):
    req = urllib.request.Request(
        base_url.rstrip('/') + '/chat/completions',
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)


def extract_text(response: dict) -> str:
    choices = response.get('choices') or []
    if not choices:
        return ''
    msg = choices[0].get('message') or {}
    content = msg.get('content', '')
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                parts.append(item.get('text', ''))
        return ''.join(parts)
    return str(content)


def main():
    parser = argparse.ArgumentParser(description='Delegate a prompt to a LiteLLM model via OpenAI-compatible API.')
    parser.add_argument('--model', required=True, help='Target model id')
    parser.add_argument('--prompt', default='', help='User prompt text')
    parser.add_argument('--system', default='', help='Optional system prompt text')
    parser.add_argument('--messages-file', default='', help='JSON file with messages list')
    parser.add_argument('--api-base', default='', help='Optional API base override')
    parser.add_argument('--temperature', type=float, default=None, help='Optional temperature override')
    parser.add_argument('--json', action='store_true', help='Return raw JSON response')
    args = parser.parse_args()

    load_env_candidates()
    settings = load_settings()
    base_url = (args.api_base or settings.get('chat_model_api_base', '')).strip()
    api_key = os.environ.get('API_KEY_OTHER', '').strip()

    if not base_url:
        raise SystemExit('chat_model_api_base missing in /a0/usr/settings.json and no --api-base provided')
    if not api_key:
        raise SystemExit('API_KEY_OTHER not found in environment or known .env files')

    messages = build_messages(args.system, args.prompt, args.messages_file or None)

    payload = {
        'model': args.model,
        'messages': messages,
    }
    if args.temperature is not None:
        payload['temperature'] = args.temperature

    response = post_chat(base_url, api_key, payload)
    if args.json:
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return

    print(extract_text(response))


if __name__ == '__main__':
    main()
