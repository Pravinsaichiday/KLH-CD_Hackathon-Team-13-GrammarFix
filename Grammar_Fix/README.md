# Grammar Fix

**PS-04 · Dangling-Else Resolver · Compiler Design Hackathon**

Grammar Fix is an interactive grammar-analysis workbench. It demonstrates the ambiguity of the dangling-else grammar, transforms the grammar into matched and unmatched productions, and compares parse trees before and after the rewrite.

## Run locally (macOS / VS Code)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
python backend/app.py
```

Open **http://127.0.0.1:5000**. Keep the terminal running while using the application.

For Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
python backend/app.py
```

Python 3.10 or newer is recommended. The application uses Flask for the backend and plain HTML, CSS and JavaScript for the frontend. No Node.js or build step is required.

## Features

- Source statement editor with built-in examples and Ctrl/Cmd + Enter shortcut.
- Lexical token stream with coloured if/else binding pairs.
- Exact parse-tree count and alternative parse-tree navigation.
- Side-by-side original and transformed parse-tree comparison.
- Download parse trees as DOT, SVG or PNG.
- Matched/unmatched grammar comparison.
- Nearest-unmatched-if binding table and parser stack trace.
- Step-by-step explanation, grammar editor and test-case builder.
- Nine built-in regression examples exposed through the API.
- Light/dark appearance toggle and responsive layout.

## Project structure

```text
Grammar_Fix/
├── backend/
│   ├── app.py
│   ├── analysis.py
│   ├── cfg_parser.py
│   └── grammar.py
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── tests/
├── requirements.txt
└── README.md
```

The backend/API and parser implementation are retained from the supplied project. The frontend is redesigned and uses the existing same-origin API routes.

## Team

**Team 13**

- 2420030290 - D. Kamal
- 2420030777 - C. Pravin Sai
- 2420090088 - H. Niranjan
