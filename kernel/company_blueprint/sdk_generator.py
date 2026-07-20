"""
SDK Generator

Generates production-shaped starter code for a company's own endpoint -
authentication, HMAC signing, retries, request IDs, and error handling,
per the spec ("Each SDK already includes Authentication, Signing,
Retries, Validation, Error Handling, Request IDs"). Uses placeholders
for the API key and webhook secret (read from the environment in every
sample) rather than embedding real values - a code sample is exactly
the kind of thing that ends up copy-pasted into a public repo, so it
should never contain a live secret.
"""

SUPPORTED_LANGUAGES = ["typescript", "javascript", "php", "python", "java"]


def _typescript(endpoint_url: str) -> str:
    return f"""import crypto from "crypto";
import {{ randomUUID }} from "crypto";

const ENDPOINT = "{endpoint_url}";
const API_KEY = process.env.ORBIT_API_KEY!;
const WEBHOOK_SECRET = process.env.ORBIT_WEBHOOK_SECRET!;

async function sendEvent(payload: Record<string, unknown>, retries = 3): Promise<Response> {{
  const body = JSON.stringify(payload);
  const signature = crypto.createHmac("sha256", WEBHOOK_SECRET).update(body).digest("hex");
  const requestId = randomUUID();

  for (let attempt = 1; attempt <= retries; attempt++) {{
    const res = await fetch(ENDPOINT, {{
      method: "POST",
      headers: {{
        "Content-Type": "application/json",
        "Authorization": `Bearer ${{API_KEY}}`,
        "X-Orbit-Signature": signature,
        "X-Orbit-Request-Id": requestId,
      }},
      body,
    }});
    if (res.ok) return res;
    if (res.status < 500 || attempt === retries) throw new Error(`Orbit request failed: ${{res.status}}`);
    await new Promise((r) => setTimeout(r, 2 ** attempt * 200));
  }}
  throw new Error("unreachable");
}}
"""


def _javascript(endpoint_url: str) -> str:
    return f"""const crypto = require("crypto");
const {{ randomUUID }} = require("crypto");

const ENDPOINT = "{endpoint_url}";
const API_KEY = process.env.ORBIT_API_KEY;
const WEBHOOK_SECRET = process.env.ORBIT_WEBHOOK_SECRET;

async function sendEvent(payload, retries = 3) {{
  const body = JSON.stringify(payload);
  const signature = crypto.createHmac("sha256", WEBHOOK_SECRET).update(body).digest("hex");
  const requestId = randomUUID();

  for (let attempt = 1; attempt <= retries; attempt++) {{
    const res = await fetch(ENDPOINT, {{
      method: "POST",
      headers: {{
        "Content-Type": "application/json",
        "Authorization": `Bearer ${{API_KEY}}`,
        "X-Orbit-Signature": signature,
        "X-Orbit-Request-Id": requestId,
      }},
      body,
    }});
    if (res.ok) return res;
    if (res.status < 500 || attempt === retries) throw new Error(`Orbit request failed: ${{res.status}}`);
    await new Promise((r) => setTimeout(r, 2 ** attempt * 200));
  }}
}}

module.exports = {{ sendEvent }};
"""


def _php(endpoint_url: str) -> str:
    return f"""<?php

$endpoint = "{endpoint_url}";
$apiKey = getenv("ORBIT_API_KEY");
$webhookSecret = getenv("ORBIT_WEBHOOK_SECRET");

function sendEvent(array $payload, int $retries = 3) {{
    global $endpoint, $apiKey, $webhookSecret;

    $body = json_encode($payload);
    $signature = hash_hmac("sha256", $body, $webhookSecret);
    $requestId = bin2hex(random_bytes(16));

    for ($attempt = 1; $attempt <= $retries; $attempt++) {{
        $ch = curl_init($endpoint);
        curl_setopt_array($ch, [
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => $body,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HTTPHEADER => [
                "Content-Type: application/json",
                "Authorization: Bearer $apiKey",
                "X-Orbit-Signature: $signature",
                "X-Orbit-Request-Id: $requestId",
            ],
        ]);
        $response = curl_exec($ch);
        $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($status >= 200 && $status < 300) return $response;
        if ($status < 500 || $attempt === $retries) {{
            throw new Exception("Orbit request failed: $status");
        }}
        usleep((2 ** $attempt) * 200000);
    }}
}}
"""


def _python(endpoint_url: str) -> str:
    return f"""import hashlib
import hmac
import json
import os
import time
import uuid

import requests

ENDPOINT = "{endpoint_url}"
API_KEY = os.environ["ORBIT_API_KEY"]
WEBHOOK_SECRET = os.environ["ORBIT_WEBHOOK_SECRET"]


def send_event(payload: dict, retries: int = 3) -> requests.Response:
    body = json.dumps(payload)
    signature = hmac.new(WEBHOOK_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    request_id = str(uuid.uuid4())

    for attempt in range(1, retries + 1):
        response = requests.post(
            ENDPOINT,
            data=body,
            headers={{
                "Content-Type": "application/json",
                "Authorization": f"Bearer {{API_KEY}}",
                "X-Orbit-Signature": signature,
                "X-Orbit-Request-Id": request_id,
            }},
        )
        if response.ok:
            return response
        if response.status_code < 500 or attempt == retries:
            response.raise_for_status()
        time.sleep((2 ** attempt) * 0.2)
    raise RuntimeError("unreachable")
"""


def _java(endpoint_url: str) -> str:
    return f"""import java.net.URI;
import java.net.http.*;
import java.util.UUID;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.util.HexFormat;

public class OrbitClient {{
    private static final String ENDPOINT = "{endpoint_url}";
    private static final String API_KEY = System.getenv("ORBIT_API_KEY");
    private static final String WEBHOOK_SECRET = System.getenv("ORBIT_WEBHOOK_SECRET");
    private static final HttpClient CLIENT = HttpClient.newHttpClient();

    public static HttpResponse<String> sendEvent(String jsonBody, int retries) throws Exception {{
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(WEBHOOK_SECRET.getBytes(), "HmacSHA256"));
        String signature = HexFormat.of().formatHex(mac.doFinal(jsonBody.getBytes()));
        String requestId = UUID.randomUUID().toString();

        for (int attempt = 1; attempt <= retries; attempt++) {{
            HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(ENDPOINT))
                .header("Content-Type", "application/json")
                .header("Authorization", "Bearer " + API_KEY)
                .header("X-Orbit-Signature", signature)
                .header("X-Orbit-Request-Id", requestId)
                .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                .build();

            HttpResponse<String> response = CLIENT.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() < 300) return response;
            if (response.statusCode() < 500 || attempt == retries) {{
                throw new RuntimeException("Orbit request failed: " + response.statusCode());
            }}
            Thread.sleep((long) Math.pow(2, attempt) * 200);
        }}
        throw new RuntimeException("unreachable");
    }}
}}
"""


_RENDERERS = {
    "typescript": _typescript,
    "javascript": _javascript,
    "php": _php,
    "python": _python,
    "java": _java,
}


def render(language: str, endpoint_url: str) -> str:
    renderer = _RENDERERS.get(language)
    if renderer is None:
        raise ValueError(f"Unsupported language '{language}' - choose one of {SUPPORTED_LANGUAGES}")
    return renderer(endpoint_url)
