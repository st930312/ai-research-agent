import json
import os
import sys
import urllib.error
import urllib.request

PROVIDERS = {
    "nvidia": ("NVIDIA_API_KEY", "https://integrate.api.nvidia.com/v1/chat/completions", "z-ai/glm-5.3-flash"),
    "zai": ("ZAI_API_KEY", "https://api.z.ai/api/paas/v4/chat/completions", "glm-5.3-flash"),
}

def main():
    provider = sys.argv[1]
    secret_name, endpoint, model = PROVIDERS[provider]
    secret = os.getenv(secret_name, "")
    if not secret:
        print(f"RESULT {provider}: MISSING_SECRET ({secret_name})")
        return 2
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "只回答 OK，不需要其他內容。"}],
        "max_tokens": 128,
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            result = json.load(resp)
        choice = (result.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        content = msg.get("content") or ""
        usage = result.get("usage") or {}
        print(f"RESULT {provider}: HTTP_200 model={result.get('model', model)!s}")
        print(f"CONTENT: {str(content)[:120]!r}")
        print(f"FINISH_REASON: {choice.get('finish_reason')}")
        print(f"USAGE: prompt={usage.get('prompt_tokens')} completion={usage.get('completion_tokens')}")
        return 0 if str(content).strip() else 3
    except urllib.error.HTTPError as exc:
        print(f"RESULT {provider}: HTTP_{exc.code}; check provider model entitlement")
        return 1
    except Exception as exc:
        print(f"RESULT {provider}: {type(exc).__name__}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
