import httpx
import time
import socket
import json
from urllib.parse import urlparse
from typing import List, Dict, Any

# --- Constants ---
SECURITY_HEADERS = [
    "Strict-Transport-Security",
    "Content-Security-Policy",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Permissions-Policy",
    "X-XSS-Protection"
]

SENSITIVE_KEYS = ["password", "token", "secret", "authorization", "apikey"]

DEFAULT_TIMEOUT = 10


# --- Utility Functions ---
def generate_recommendations(entry: Dict[str, Any]) -> List[str]:
    recos = []
    if not entry["security_headers_ok"]:
        recos.append("Ajouter les headers de sécurité manquants: " + ", ".join(entry["missing_security_headers"]))
    if entry["open_redirect_check"]:
        recos.append("Corriger une possible faille de redirection ouverte.")
    if entry["sensitive_data_found"]:
        recos.append("Masquer ou sécuriser les données sensibles exposées: " + ", ".join(entry["sensitive_data_found"]))
    if not entry["dns_resolvable"]:
        recos.append("Vérifier la résolution DNS du domaine.")
    if entry["error"]:
        recos.append("Corriger l'erreur détectée: " + entry["error"])
    return recos


def compute_entry_score(entry: Dict[str, Any]) -> int:
    score = 0
    if entry.get("status_code") and entry["status_code"] < 400:
        score += 30
    if entry.get("security_headers_ok"):
        score += 20
    if not entry.get("sensitive_data_found"):
        score += 20
    if entry.get("dns_resolvable"):
        score += 10
    if not entry.get("error"):
        score += 20
    return score


# --- Main Audit Function ---
def audit_api(base_url: str, endpoints: List[str]) -> Dict[str, Any]:
    results = []
    global_start = time.time()

    for endpoint in endpoints:
        url = endpoint if endpoint.startswith("http") else f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        result = {
            "url": url,
            "status_code": None,
            "response_time_ms": None,
            "headers": {},
            "security_headers_ok": True,
            "missing_security_headers": [],
            "content_type": None,
            "error": None,
            "json_keys": [],
            "sensitive_data_found": [],
            "is_https": url.startswith("https://"),
            "dns_resolvable": True,
            "open_redirect_check": False,
            "recommendations": []
        }

        try:
            start = time.time()
            response = httpx.get(url, timeout=DEFAULT_TIMEOUT)
            duration = round((time.time() - start) * 1000, 2)
            headers = response.headers

            result.update({
                "status_code": response.status_code,
                "response_time_ms": duration,
                "headers": dict(headers),
                "content_type": headers.get("Content-Type", "Unknown")
            })

            # Security header checks
            missing = [h for h in SECURITY_HEADERS if h not in headers]
            result["missing_security_headers"] = missing
            result["security_headers_ok"] = not missing

            # JSON inspection
            if "application/json" in headers.get("Content-Type", ""):
                try:
                    data = response.json()
                    keys = list(data.keys()) if isinstance(data, dict) else []
                    result["json_keys"] = keys
                    result["sensitive_data_found"] = [k for k in keys if any(s in k.lower() for s in SENSITIVE_KEYS)]
                except json.JSONDecodeError:
                    result["error"] = "Réponse JSON invalide"

            # Redirect check
            if response.status_code in [301, 302, 307, 308]:
                loc = headers.get("Location", "")
                if loc.startswith("http"):
                    result["open_redirect_check"] = True

        except httpx.TimeoutException:
            result["error"] = "Timeout"
        except httpx.RequestError as e:
            result["error"] = f"Erreur de requête: {str(e)}"
        except Exception as e:
            result["error"] = f"Erreur inconnue: {str(e)}"

        # DNS resolution
        try:
            domain = urlparse(url).hostname
            socket.gethostbyname(domain)
        except Exception:
            result["dns_resolvable"] = False

        # Recommendations and scoring
        result["recommendations"] = generate_recommendations(result)
        result["score"] = compute_entry_score(result)

        results.append(result)

    audit_duration = round(time.time() - global_start, 2)
    valid_responses = [r for r in results if r["status_code"] and r["status_code"] < 400]
    avg_response = round(sum(r["response_time_ms"] or 0 for r in results) / len(results), 2)
    global_score = round(sum(r["score"] for r in results) / len(results)) if results else 0

    return {
        "summary": {
            "nb_endpoints": len(endpoints),
            "success": len(valid_responses),
            "errors": len(results) - len(valid_responses),
            "avg_response_time_ms": avg_response,
            "audit_duration_s": audit_duration,
            "score": global_score
        },
        "details": results
    }
