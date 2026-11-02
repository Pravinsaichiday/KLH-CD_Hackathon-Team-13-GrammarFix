
# Grammar Fix

**An interactive Dangling-Else Resolver for Compiler Design (PS-04)**

Grammar Fix is a browser-based grammar analysis workbench that demonstrates the classic dangling-`else` ambiguity in nested conditional statements. It parses an input against an ambiguous context-free grammar, displays the possible parse trees, rewrites the grammar into matched and unmatched statement productions, and shows the single interpretation selected by the nearest-unmatched-`if` rule.

The project was developed by **Team 13** for the Compiler Design hackathon, with a focus on making top-down parsing concepts visible and easier to explain.

## Project at a glance

- **Project:** Grammar Fix
- **Problem statement:** PS-04, Dangling-Else Resolver
- **Course area:** Compiler Design, Unit II: Parsing (Top-Down)
- **Backend:** Python and Flask
- **Frontend:** HTML5, CSS3 and vanilla JavaScript
- **Tree rendering:** Inline SVG in the browser
- **Automated tests:** pytest

## Interface preview

### Workbench and parse-tree comparison

![Grammar Fix workbench showing the input editor, token stream, and before/after parse trees](docs/screenshots/01-workbench-and-parse-trees.png)

### Grammar transformation and explanation

![Grammar transformation, matched and unmatched productions, and step-by-step explanation](docs/screenshots/02-grammar-and-step-explanation.png)

### Validation results and team credits

![Validation section and project footer](docs/screenshots/03-validation-and-footer.png)

## Features

### Grammar analysis

- Accepts nested `if`, `then`, and optional `else` statements in the project's mini-language.
- Tokenizes the input and displays token positions.
- Parses the source using the original ambiguous grammar.
- Counts and enumerates valid parse trees for the input.
- Identifies which `if` each `else` attaches to under the nearest-unmatched-`if` convention.

### Grammar transformation

- Displays the original dangling-`else` grammar.
- Rewrites the grammar using `matched` and `unmatched` nonterminals.
- Parses the input with the transformed grammar.
- Compares the original alternative parse trees with the resolved tree.
- Explains the transformation through a step-by-step analysis and binding details.

### Interactive frontend

- Source statement editor and ready-made examples.
- Token stream with `if`/`else` binding highlights.
- Side-by-side before/after parse-tree visualization.
- Parse-tree navigation and downloads in DOT, SVG and PNG formats.
- Grammar comparison and nearest-unmatched-`if` binding table.
- Test-case builder for varying nesting depth and `else` placement.
- Built-in regression suite.
- Responsive layout and light/dark theme toggle.

## Technologies used

| Technology | Role in the project |
|---|---|
| **Python 3** | Implements the grammar model, tokenizer, parser and analysis logic. |
| **Flask** | Serves the frontend and exposes the analysis API. |
| **HTML5** | Defines the semantic structure of the web interface. |
| **CSS3** | Handles layout, responsive styling, themes and visual states. |
| **JavaScript (ES2020)** | Connects the UI to the API, manages interactions and renders parse trees. |
| **SVG** | Renders parse trees directly in the browser. |
| **pytest** | Runs the automated parser and grammar regression tests. |
| **Git and GitHub** | Version control and project collaboration. |

No Node.js installation, frontend framework, database, or Graphviz installation is required to run the application. Graphviz is not required at runtime because the browser renders the trees as SVG. DOT files can be downloaded for optional external rendering.

## How it works

The project uses two grammar views to demonstrate the ambiguity and its resolution.

### 1. Original ambiguous grammar

```text
stmt -> if E then stmt
      | if E then stmt else stmt
      | S
```

The two conditional productions share the prefix `if E then stmt`. When an `else` follows a nested conditional, the original grammar can permit more than one attachment and therefore more than one parse tree.

### 2. Matched/unmatched grammar

```text
stmt      -> matched | unmatched
matched   -> if E then matched else matched
           | S
unmatched -> if E then stmt
           | if E then matched else unmatched
```

The transformed grammar separates fully matched statements from statements that still contain an unmatched `if`. This structurally enforces the nearest-unmatched-`if` convention.

### 3. Analysis pipeline

```text
Source statement
      |
      v
Tokenization
      |
      v
Parse with original grammar
      |
      v
Enumerate valid parse trees
      |
      v
Determine nearest-unmatched-if bindings
      |
      v
Transform grammar to matched/unmatched form
      |
      v
Parse with transformed grammar
      |
      v
Compare trees, bindings and explanations in the UI
```

## Project structure

```text
GrammarFix/
├── backend/
│   ├── app.py             # Flask application and API routes
│   ├── analysis.py        # Ambiguity analysis, bindings, examples and test cases
│   ├── cfg_parser.py      # Tokenizer and context-free grammar parser
│   └── grammar.py         # Grammar model and matched/unmatched transformation
├── frontend/
│   ├── index.html         # Main application page
│   ├── style.css          # Layout, responsive styles and themes
│   └── app.js             # API integration and interactive SVG tree rendering
├── tests/
│   ├── conftest.py
│   └── test_resolver.py   # Grammar and parser regression tests
├── docs/
│   ├── GrammarFix_Presentation.pptx
│   └── screenshots/
├── .github/
│   └── workflows/
│       └── tests.yml      # GitHub Actions test workflow
├── requirements.txt
├── run_mac.command
├── .gitignore
└── README.md
```

## Getting started

### Requirements

- Python 3.10 or newer
- pip
- A modern web browser

### macOS / Linux

Open a terminal in the project root and run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
python backend/app.py
```

Open **http://127.0.0.1:5000** in your browser. Keep the terminal open while using the application. Press `Ctrl+C` in the terminal to stop the server.

On macOS, `run_mac.command` is also provided as a convenience launcher. You may need to allow it to run with `chmod +x run_mac.command` first.

### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
python backend/app.py
```

Then open **http://127.0.0.1:5000**.

## API endpoints

The Flask backend exposes these same-origin endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/default` | Returns the default grammar and built-in examples. |
| `POST` | `/api/analyze` | Tokenizes and analyzes a source statement, returning parse trees, bindings, grammar details and explanation steps. |
| `POST` | `/api/witness` | Searches for short strings that demonstrate grammar ambiguity. |
| `POST` | `/api/generate` | Generates a nested conditional test case based on nesting depth and selected `else` levels. |
| `GET` | `/api/tests` | Runs and returns the built-in regression cases. |

Example request to analyze a statement:

```bash
curl -X POST http://127.0.0.1:5000/api/analyze \
  -H 'Content-Type: application/json' \
  -d '{"input":"if e1 then if e2 then s1 else s2"}'
```

## Demo inputs

The mini-language uses `if`, `then`, `else`, condition symbols such as `e1` and simple statement symbols such as `s1`.

| Demonstration | Input | Expected parses before | Expected parses after |
|---|---|---:|---:|
| Single `if` | `if e1 then s1` | 1 | 1 |
| Single `if-else` | `if e1 then s1 else s2` | 1 | 1 |
| Classic dangling `else` | `if e1 then if e2 then s1 else s2` | 2 | 1 |
| Nested `if` with two `else` clauses | `if e1 then if e2 then s1 else s2 else s3` | 1 | 1 |
| Three nested `if` statements and one `else` | `if e1 then if e2 then if e3 then s1 else s2` | 3 | 1 |
| Invalid: `else` without `if` | `s1 else s2` | 0 | 0 |

The grammar editor supports custom grammar input within the syntax supported by the backend.

## Tests and validation

Run the complete automated test suite from the project root:

```bash
python -m pytest -q
```

The project test suite was run while preparing this repository package and completed with **59 passed**. The web interface also includes a separate built-in analysis suite that can be run from the Test suite panel.

A GitHub Actions workflow is included to run the pytest suite on pushes and pull requests.

## Presentation

The project presentation is available at [`docs/GrammarFix_Presentation.pptx`](docs/GrammarFix_Presentation.pptx). Screenshots of the running interface are available in [`docs/screenshots/`](docs/screenshots/).

## Team 13

- **2420030290 - D. Kamal**
- **2420030777 - C. Pravin Sai**
- **2420090088 - H. Niranjan**

**Faculty Coordinator:** Mrs. E. Uma Shankari

---

Made by **Team 13** for the Compiler Design Hackathon.
