from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "cases"
UI = ROOT / "ui" / "index.html"


def clean_text(value):
    text = str(value)
    return text.replace("â€”", "-").replace("â€“", "-").replace("—", "-").replace("–", "-")


def clean_payload(value):
    if isinstance(value, str):
        return clean_text(value)
    if isinstance(value, list):
        return [clean_payload(item) for item in value]
    if isinstance(value, dict):
        return {key: clean_payload(item) for key, item in value.items()}
    return value


def case_directories() -> dict[int, Path]:
    found: dict[int, Path] = {}
    candidates = sorted(CASES.glob("issue-*"))
    live = CASES / "live"
    if live.exists():
        candidates.extend(sorted(live.glob("issue-*")))
    for directory in candidates:
        suffix = directory.name.removeprefix("issue-")
        if suffix.isdigit():
            found[int(suffix)] = directory
    return found


class VerdictServer(ThreadingHTTPServer):
    def __init__(self, address, handler, session_token: str):
        super().__init__(address, handler)
        self.session_token = session_token


class Handler(BaseHTTPRequestHandler):
    server_version = "VerdictRoom/1.0"

    @property
    def token(self) -> str:
        return self.server.session_token

    def _send(self, status: int, payload, content_type: str = "application/json"):
        body = (
            clean_text(payload).encode("utf-8")
            if isinstance(payload, str)
            else json.dumps(clean_payload(payload), ensure_ascii=False, indent=2).encode("utf-8")
        )
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _safe_post(self) -> bool:
        host_header = self.headers.get("Host", "")
        host = host_header.split(":")[0]
        origin = self.headers.get("Origin")
        if host not in {"127.0.0.1", "localhost"}:
            self._send(HTTPStatus.BAD_REQUEST, {"error": "invalid Host"})
            return False
        allowed_origins = {
            f"http://{host_header}",
            f"http://localhost:{host_header.rsplit(':', 1)[-1]}",
        }
        if origin not in allowed_origins:
            self._send(HTTPStatus.FORBIDDEN, {"error": "invalid Origin"})
            return False
        if not secrets.compare_digest(self.headers.get("X-Verdict-Token", ""), self.token):
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "invalid session token"})
            return False
        return True

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 100_000:
            raise ValueError("request body too large")
        body = self.rfile.read(length)
        payload = json.loads(body or b"{}")
        if not isinstance(payload, dict):
            raise TypeError("request JSON must be an object")
        return payload

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            if not UI.exists():
                self._send(HTTPStatus.NOT_FOUND, {"error": "ui/index.html missing"})
                return
            html = UI.read_text(encoding="utf-8")
            html = html.replace("__VERDICT_SESSION_TOKEN__", json.dumps(self.token))
            self._send(HTTPStatus.OK, html, "text/html")
            return
        if path == "/api/cases":
            self._send(HTTPStatus.OK, {"cases": self._list_cases()})
            return
        parts = [part for part in path.split("/") if part]
        if len(parts) in {3, 4} and parts[:2] == ["api", "cases"] and parts[2].isdigit():
            issue = int(parts[2])
            if len(parts) == 3 or (len(parts) == 4 and parts[3] == "ledger"):
                self._case_response(issue)
                return
        self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def _list_cases(self) -> list[dict]:
        result = []
        for issue, directory in sorted(case_directories().items()):
            casefile = directory / "casefile.json"
            if not casefile.exists():
                continue
            data = json.loads(casefile.read_text(encoding="utf-8"))
            ledger = directory / "ledger.json"
            result.append(
                {
                    "issue": issue,
                    "title": data.get("issue_title", ""),
                    "source": data.get("source", "live"),
                    "pr_count": len(data.get("prs", [])),
                    "ledger_rows": len(json.loads(ledger.read_text(encoding="utf-8")))
                    if ledger.exists()
                    else 0,
                }
            )
        return result

    def _case_response(self, issue: int):
        directory = case_directories().get(issue)
        if directory is None:
            self._send(HTTPStatus.NOT_FOUND, {"error": f"case {issue} not found"})
            return
        casefile = directory / "casefile.json"
        if not casefile.exists():
            self._send(HTTPStatus.NOT_FOUND, {"error": "casefile.json missing"})
            return
        case = json.loads(casefile.read_text(encoding="utf-8"))
        ledger_path = directory / "ledger.json"
        ledger = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else []
        overrides_path = directory / "overrides.json"
        if overrides_path.exists():
            overrides = json.loads(overrides_path.read_text(encoding="utf-8"))
            for row in ledger:
                override = overrides.get(row.get("claim_id"))
                if override:
                    row["status"] = override["status"]
                    row["rationale"] = override["note"]
                    row["judged_by"] = override["approver"]
        drafts = {}
        drafts_dir = directory / "drafts"
        if drafts_dir.exists():
            drafts = {
                path.stem: clean_text(path.read_text(encoding="utf-8"))
                for path in drafts_dir.glob("*.md")
            }
        approvals = {}
        approvals_dir = directory / "approvals"
        if approvals_dir.exists():
            approvals = {
                path.stem: json.loads(path.read_text(encoding="utf-8"))
                for path in approvals_dir.glob("*.json")
            }
        agent_files = {}
        for filename in ("verdicts.json", "challenges.json", "rebuttals.json"):
            path = directory / filename
            agent_files[filename] = (
                json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            )
        self._send(
            HTTPStatus.OK,
            {
                "issue": issue,
                "case": case,
                "ledger": ledger,
                "drafts": drafts,
                "approvals": approvals,
                "verdicts": agent_files["verdicts.json"],
                "challenges": agent_files["challenges.json"],
                "rebuttals": agent_files["rebuttals.json"],
            },
        )

    def do_POST(self):
        if not self._safe_post():
            return
        try:
            payload = self._read_json()
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        parts = [part for part in urlparse(self.path).path.split("/") if part]
        if len(parts) != 4 or parts[:2] != ["api", "cases"]:
            self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        issue_text, action = parts[2], parts[3]
        if not issue_text.isdigit():
            self._send(HTTPStatus.BAD_REQUEST, {"error": "issue must be numeric"})
            return
        issue = int(issue_text)
        directory = case_directories().get(issue)
        if directory is None:
            self._send(HTTPStatus.NOT_FOUND, {"error": f"case {issue} not found"})
            return
        if action == "override":
            self._override(directory, payload)
        elif action == "draft":
            self._draft(directory, payload)
        elif action == "approve":
            self._approve(directory, payload)
        else:
            self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def _override(self, directory: Path, payload: dict):
        claim_id = str(payload.get("claim_id", "")).strip()
        note = str(payload.get("note", "")).strip()
        approver = str(payload.get("approver", "")).strip()
        status = str(payload.get("status", "")).strip()
        if (
            not claim_id
            or not note
            or not approver
            or status
            not in {
                "VERIFIED",
                "UNVERIFIED",
                "CONTRADICTED",
                "NOT_CHECKABLE",
            }
        ):
            self._send(HTTPStatus.BAD_REQUEST, {"error": "invalid override"})
            return
        path = directory / "overrides.json"
        overrides = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        overrides[claim_id] = {
            "status": status,
            "note": note,
            "approver": approver,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        path.write_text(
            json.dumps(overrides, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        ledger_path = directory / "ledger.json"
        if ledger_path.exists():
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            changed = False
            for row in ledger:
                if row.get("claim_id") == claim_id:
                    row["status"] = status
                    row["rationale"] = note
                    row["judged_by"] = approver
                    changed = True
                    break
            if changed:
                ledger_path.write_text(
                    json.dumps(ledger, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
        self._send(HTTPStatus.OK, {"saved": claim_id})

    def _draft(self, directory: Path, payload: dict):
        from .ruling import draft_hash, normalize_draft_text

        pr = payload.get("pr")
        draft = normalize_draft_text(str(payload.get("draft", "")))
        if not isinstance(pr, int) or not draft:
            self._send(HTTPStatus.BAD_REQUEST, {"error": "pr and draft are required"})
            return
        drafts = directory / "drafts"
        drafts.mkdir(exist_ok=True)
        path = drafts / f"{pr}.md"
        path.write_text(clean_text(draft) + "\n", encoding="utf-8")
        self._send(
            HTTPStatus.OK,
            {"pr": pr, "draft_hash": draft_hash(draft)},
        )

    def _approve(self, directory: Path, payload: dict):
        from .ruling import normalize_draft_text, save_pr_approval

        pr = payload.get("pr")
        draft = normalize_draft_text(str(payload.get("draft", "")))
        approver = str(payload.get("approver", "")).strip()
        outcome = str(payload.get("outcome", "")).strip()
        human_comments = clean_text(str(payload.get("human_comments", "")).strip())
        if not isinstance(pr, int) or not draft or not approver or not outcome:
            self._send(
                HTTPStatus.BAD_REQUEST,
                {"error": "pr, draft, approver, and outcome required"},
            )
            return
        approval = save_pr_approval(
            directory,
            pr,
            draft,
            approver,
            outcome,
            human_comments,
        )
        self._send(HTTPStatus.OK, approval)

    def log_message(self, format, *args):
        return
