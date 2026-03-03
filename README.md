# smartsh

A shareable terminal assistant shell for Linux that adds:

- Autocorrect for common command typos
- Right-side short command explanation while typing
- Dropdown command suggestions (`Ctrl+Space`)
- Personalized ranking based on local usage frequency and recency
- Directory typo help for `cd` (single-match auto-fix, multi-match list)
- Command history suggestions
- Plain-English explanation when commands fail
- Confirmation prompt for risky commands

## Quick start

```bash
chmod +x install.sh
./install.sh
smartsh
lazyterminal
```

## Features

- Typo map examples: `gti` -> `git`, `pyhton` -> `python`, `sl` -> `ls`
- Fuzzy command correction for unknown command names
- Built-ins:
  - `help`
  - `smartsh config`
  - `smartsh reload`
  - `smartsh learning status`
  - `smartsh learning reset`

## Personalization (local-only)

smartsh learns from successful commands and ranks suggestions to surface what you use most.

Learned data is stored only on your machine in:

```bash
~/.local/share/smartsh/learning.json
```

Captured fields per command:

- Full command string
- Base command (first token)
- Last-used timestamp
- Working directory frequency
- Previous-command context frequency

No network calls, cloud sync, or telemetry upload are used.

Sensitive command filtering is enabled via denylist patterns. Matching commands are not learned.
Additionally, sensitive-looking commands are guarded at runtime:
- first attempt is blocked with an error message,
- running the exact same command again asks for confirmation.

Default ranking formula:

```text
score = 0.55*match + 0.20*frequency + 0.20*recency + 0.05*context
```

where:
- `match`: prefix/substring/fuzzy relevance to current input
- `frequency`: normalized usage count
- `recency`: exponential decay by `learning_decay_days`
- `context`: same directory / previous base command bonus

## Config

Config file:

```bash
~/.config/smartsh/config.json
```

Useful keys:

- `autocorrect_enabled`
- `autocorrect_threshold`
- `command_explain_enabled`
- `error_explain_enabled`
- `confirm_dangerous`
- `typo_map`
- `custom_commands`
- `learning_enabled`
- `learning_top_n`
- `learning_decay_days`
- `learning_denylist_patterns`

After changing config run:

```bash
smartsh
# inside smartsh
smartsh reload
smartsh learning status
smartsh learning reset
```

If `learning.json` is corrupted or schema is unsupported, smartsh resets to safe defaults automatically.

## Export a shareable bundle

```bash
chmod +x export_bundle.sh
./export_bundle.sh
```

Output:

```bash
dist/smartsh_bundle_YYYYMMDD_HHMMSS.tar.gz
```

## Install from bundle (friend's machine)

```bash
tar -xzf smartsh_bundle_*.tar.gz
cd smartsh_bundle_*
./install.sh
smartsh
lazyterminal
```

## Uninstall

```bash
./uninstall.sh
```

## Notes

- Tested on bash-compatible systems.
- Requires Python 3.10+.
