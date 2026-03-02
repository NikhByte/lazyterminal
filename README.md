# smartsh

A shareable terminal assistant shell for Linux that adds:

- Autocorrect for common command typos
- Dropdown command suggestions (`Ctrl+Space`)
- Command history suggestions
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

## Config

Config file:

```bash
~/.config/smartsh/config.json
```

Useful keys:

- `autocorrect_enabled`
- `autocorrect_threshold`
- `confirm_dangerous`
- `typo_map`
- `custom_commands`

After changing config run:

```bash
smartsh
# inside smartsh
smartsh reload
```

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
