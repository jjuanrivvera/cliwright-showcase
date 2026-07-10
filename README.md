# cliwright-showcase

The registry behind **[cliwright.jjuanrivvera.com](https://cliwright.jjuanrivvera.com)** — a
directory of agent-native command-line tools built with
[cliwright](https://github.com/jjuanrivvera/cliwright), the generator that turns any HTTP API
into a production-grade CLI (keyring auth, resilient client, MCP server, agent guard, signed
releases) against one deterministic acceptance gate.

The site is generated from this repo. **Add your CLI with a pull request** — a bot validates
your entry before it can merge.

## Add your CLI

1. Fork this repo.
2. Add `registry/<your-tool>.yaml` (copy any existing file). The filename must equal the
   entry `name`.
3. Open a PR. The **Validate registry** check must pass (green) for it to merge; on merge, the
   site redeploys automatically.

Only tools **built with cliwright** belong here — that's the whole point of the showcase.

### Entry format

```yaml
name: mytool                 # kebab-case; must match the filename
binary: mytool               # the command users type
description: One sentence.    # what it does, ≤160 chars, no marketing
wraps: The API it wraps       # e.g. Stripe, Slack Web API
repo: https://github.com/you/mytool
author: your-github-handle
install:                      # at least one method
  brew: brew install you/tap/mytool
  go: go install github.com/you/mytool/cmd/mytool@latest
tags: [devops, ai-agent]      # optional, lowercase
agent_ready: true             # optional; ships an MCP server + agent guard (default true)
```

The full schema is in [`schema/entry.schema.json`](schema/entry.schema.json).

## Local preview

```bash
pip install pyyaml jsonschema
python3 scripts/build.py        # validate + write site/registry.json
python3 -m http.server -d site  # open http://localhost:8000
```

## How it works

- `registry/*.yaml` — one file per tool (the source of truth; edited by PRs).
- `scripts/build.py` — validates every entry against the schema and compiles
  `site/registry.json`. CI runs it on PRs (gate) and on merge (deploy).
- `site/` — a self-contained static site (no framework, no external requests) that renders the
  registry client-side. Served on GitHub Pages at the `site/CNAME` subdomain.

## License

MIT — the registry data is contributed by its authors; each tool links to its own source.
