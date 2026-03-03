# GitLab Contribution Tracker

A macOS menu bar application that tracks your daily GitLab push events and displays them in the menu bar.

## Features

- Real-time push count in the menu bar
- Per-project push breakdown
- Auto-refresh every 60 seconds (configurable)
- Auto-start on login
- Dynamic user profile resolution from token
- Contribution reminder notification if no pushes by 15:00

## Install via Homebrew

```bash
brew tap acanguven/tap
brew install --cask gitlab-contribution-tracker
```

## Quick Install (from source)

```bash
./install.sh
```

The install script will:
1. Create a Python virtual environment
2. Install dependencies
3. Build the macOS application (py2app)
4. Copy it to `~/Applications/`
5. Set up auto-start via LaunchAgent
6. Launch the application

## Manual Run (Development)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Configuration

Settings are stored in `~/.config/gitlab-contribution-tracker/config.json`:

```json
{
  "token": "your-gitlab-private-token",
  "gitlab_base_url": "https://gitlab.trendyol.com",
  "refresh_interval_seconds": 60
}
```

| Key | Description | Default |
|-----|-------------|---------|
| `token` | GitLab Private Access Token (required) | `""` |
| `gitlab_base_url` | GitLab instance URL | `https://gitlab.trendyol.com` |
| `refresh_interval_seconds` | How often to poll for new events | `60` |

The token must be set in the config file or via the **Settings...** option in the menu bar. The app uses this token to resolve your GitLab username automatically via the `/api/v4/user` endpoint.

## Menu Bar Indicators

| Icon | Meaning |
|------|---------|
| ⬆ 0 | No pushes today |
| 🟦 N | 1-9 pushes |
| 🟩 N | 10-19 pushes |
| 🟧 N | 20-29 pushes |
| 🟥 N | 30+ pushes |

## Uninstall

```bash
./uninstall.sh
```

## Requirements

- macOS 12+
- Python 3.9+
