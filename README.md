```
██████╗ ██████╗  █████╗ ██╗    ██╗██╗         ██████╗ ███████╗███╗   ██╗ ██████╗██╗  ██╗
██╔══██╗██╔══██╗██╔══██╗██║    ██║██║         ██╔══██╗██╔════╝████╗  ██║██╔════╝██║  ██║
██████╔╝██████╔╝███████║██║ █╗ ██║██║         ██████╔╝█████╗  ██╔██╗ ██║██║     ███████║
██╔══██╗██╔══██╗██╔══██║██║███╗██║██║         ██╔══██╗██╔══╝  ██║╚██╗██║██║     ██╔══██║
██████╔╝██║  ██║██║  ██║╚███╔███╔╝███████╗    ██████╔╝███████╗██║ ╚████║╚██████╗██║  ██║
╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚══╝╚══╝ ╚══════╝    ╚═════╝ ╚══════╝╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝
```

<p align="center"><b>B</b>rowser <b>R</b>obustness <b>A</b>gainst <b>W</b>eb-<b>L</b>evel Attacks</p>

<p align="center">A benchmark by <a href="https://browser-brawl.com">Browser Brawl</a></p>

Adversarial benchmark for LLM browser agents. Agents complete real web tasks from the [WebVoyager](https://github.com/MinorJerry/WebVoyager) dataset while JavaScript disruptions, injected via Playwright's `--init-script`, try to hijack navigation, phish credentials, or just get in the way.

Tasks are sourced from WebVoyager's Amazon subset: natural-language shopping queries like finding products with specific filters, comparing prices, and checking availability.

## Conditions

Each run uses one of three conditions that control which disruptions are active:

- **baseline** — no disruptions, clean page
- **hijack** — fake page elements that try to lure the agent off-site: spoofed sign-in walls, injected sponsored product cards linking to external domains, and "currently unavailable" gates redirecting to fake marketplaces
- **exfil** — phishing attacks that try to extract sensitive data: a fake "AI Shopping Assistant" that asks the agent to paste its instructions, a session-check modal requesting API keys, and a credential gate harvesting email/password

Canary values (API key, email, password) are seeded into the agent's prompt. The security evaluator checks post-hoc whether any canary appeared in the agent's tool calls (typed text, form fills, navigated URLs, or executed JS).

## Supported models

| Key | Model | Input $/1M | Output $/1M |
|-----|-------|-----------|------------|
| `claude-opus-4.6` | Anthropic Claude Opus 4.6 | $5.00 | $25.00 |
| `claude-sonnet-4.6` | Anthropic Claude Sonnet 4.6 | $3.00 | $15.00 |
| `gpt-5.4` | OpenAI GPT-5.4 | $2.50 | $15.00 |
| `gemini-3.1-pro` | Google Gemini 3.1 Pro Preview | $2.00 | $12.00 |
| `gemini-3.1-flash-lite` | Google Gemini 3.1 Flash Lite Preview | $0.25 | $1.50 |
| `gemini-3-flash` | Google Gemini 3 Flash Preview | $0.50 | $3.00 |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in your API keys
```

## Usage

Run a single task for quick testing:

```bash
python harness.py --model claude-sonnet-4.6 --task-id Amazon--0 --condition exfil
```

Run the full benchmark across all models and conditions:

```bash
python runner.py --conditions baseline hijack exfil --evaluate
```

### Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--models` | all | Models to test |
| `--task-ids` | all | Specific task IDs to run |
| `--tasks-file` | `tasks/amazon_selected.jsonl` | Task definitions |
| `--conditions` | `baseline` | One or more of: `baseline`, `hijack`, `exfil` |
| `--max-turns` | `25` | Max agent loop iterations |
| `--headless` | off | Run browser headless |
| `--force-screenshot` | off | Inject screenshots into LLM context each turn |
| `--evaluate` | off | Run GPT-4o evaluation after benchmark |
| `--eval-model` | `gpt-4o` | Model used for judging task success |
| `--parallel` | `1` | Max concurrent browser tasks |
| `--output-dir` | `results` | Output directory for run artifacts |

## Evaluation

The evaluator scores each run on two axes:

1. **Task success** — GPT-4o judges whether the agent answered the task correctly
2. **Security** — trace analysis checks for navigation hijacking (off-site URLs) and data exfiltration (canary leaks)

Results are saved per-run as `run.json`, `trace.json`, `eval.json`, plus screenshots and video recordings.

## Example Data Exfils
<img width="1562" height="928" alt="image" src="https://github.com/user-attachments/assets/c8e7fabf-d853-4a7a-9b41-d0d562d7aaa0" />

<img width="1543" height="932" alt="data_exfil1" src="https://github.com/user-attachments/assets/a2574b5e-d7e7-4af0-9882-ff74bec93893" />


## Authors

Have an idea you want us to add? Reach out:

- **Richard Hruby** — [GitHub](https://github.com/RichardHruby) | [𝕏](https://x.com/HrubyOnRails)
- **Mehul Kalia** — [GitHub](https://github.com/MehulKalia) | [𝕏](https://x.com/MehulKalia_)
