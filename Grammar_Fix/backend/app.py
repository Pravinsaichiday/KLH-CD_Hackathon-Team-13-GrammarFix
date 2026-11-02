"""Flask API + static file server for GrammarFix.

Run:  python backend/app.py      then open http://localhost:5000
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request, send_from_directory  # noqa: E402

from analysis import (  # noqa: E402
    analyze, default_payload, find_witnesses, generate_case, run_test_suite,
)
from cfg_parser import ParseInputError  # noqa: E402
from grammar import GrammarError  # noqa: E402

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
app = Flask(__name__, static_folder=None)


@app.after_request
def add_cors(resp):  # lets you open the frontend from another origin during development
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


def _json():
    return request.get_json(silent=True) or {}


def _guard(fn):
    try:
        return jsonify(fn())
    except (GrammarError, ParseInputError) as exc:
        return jsonify({"error": str(exc)}), 400


@app.get("/api/default")
def api_default():
    return jsonify(default_payload())


@app.post("/api/analyze")
def api_analyze():
    d = _json()
    return _guard(lambda: analyze(d.get("input", ""), d.get("grammar")))


@app.post("/api/witness")
def api_witness():
    d = _json()
    return _guard(lambda: find_witnesses(d.get("grammar"), int(d.get("max_len", 11))))


@app.post("/api/generate")
def api_generate():
    d = _json()
    return _guard(lambda: generate_case(int(d.get("depth", 2)), d.get("else_levels", [])))


@app.get("/api/tests")
def api_tests():
    results = run_test_suite()
    return jsonify({"passed": sum(r["passed"] for r in results), "total": len(results), "results": results})


@app.get("/")
def index():
    return send_from_directory(FRONTEND, "index.html")


@app.get("/<path:name>")
def static_files(name):
    return send_from_directory(FRONTEND, name)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False)
