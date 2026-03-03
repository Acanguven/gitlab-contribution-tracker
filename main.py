#!/usr/bin/env python3
"""GitLab Contribution Tracker - macOS Menu Bar Application"""

import json
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

import webbrowser

import rumps

CONFIG_DIR = Path.home() / ".config" / "gitlab-contribution-tracker"
CONFIG_FILE = CONFIG_DIR / "config.json"
CACHE_FILE = CONFIG_DIR / "events_cache.json"

DEFAULT_CONFIG = {
    "token": "",
    "gitlab_base_url": "",
    "refresh_interval_seconds": 60,
}


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        merged = {**DEFAULT_CONFIG, **cfg}
        return merged
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def fetch_push_events(token, gitlab_base_url):
    api_url = f"{gitlab_base_url}/api/v4"
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    url = f"{api_url}/events?action=pushed&after={yesterday}&per_page=100"

    req = Request(url)
    req.add_header("PRIVATE-TOKEN", token)

    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return data if isinstance(data, list) else []
    except (URLError, json.JSONDecodeError, OSError):
        return None


def count_pushes_today(events):
    if not events:
        return 0, {}
    today = datetime.now().strftime("%Y-%m-%d")
    project_counts = {}
    total = 0
    for ev in events:
        created = ev.get("created_at", "")
        if created.startswith(today):
            total += 1
            proj_id = ev.get("project_id", "unknown")
            project_counts[proj_id] = project_counts.get(proj_id, 0) + 1
    return total, project_counts


def resolve_project_names(events, token, gitlab_base_url):
    names = {}
    for ev in events:
        pid = ev.get("project_id")
        if pid and pid not in names:
            pp = ev.get("project", {})
            path = pp.get("path_with_namespace")
            if path:
                names[pid] = path
            else:
                names[pid] = _fetch_project_path(pid, token, gitlab_base_url) or str(pid)
    return names


def fetch_current_username(token, gitlab_base_url):
    url = f"{gitlab_base_url}/api/v4/user"
    req = Request(url)
    req.add_header("PRIVATE-TOKEN", token)
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return data.get("username")
    except (URLError, json.JSONDecodeError, OSError):
        return None


def _fetch_project_path(project_id, token, gitlab_base_url):
    url = f"{gitlab_base_url}/api/v4/projects/{project_id}"
    req = Request(url)
    req.add_header("PRIVATE-TOKEN", token)
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return data.get("path_with_namespace")
    except (URLError, json.JSONDecodeError, OSError):
        return None


class GitLabTracker(rumps.App):
    def __init__(self):
        super().__init__("⬆ -", quit_button=None)
        self.config = load_config()
        self.events = []
        self.push_count = 0
        self.project_counts = {}
        self.project_names = {}
        self.last_update = None
        self.error_state = False
        self.username = None
        self._reminder_shown_date = None

        self._project_keys = []

        self.menu = [
            rumps.MenuItem("Today's Pushes: -", callback=self.open_profile),
            rumps.separator,
            rumps.MenuItem("Last update: -", callback=None),
            rumps.MenuItem("Refresh Now", callback=self.manual_refresh),
            rumps.separator,
            rumps.MenuItem("Settings...", callback=self.open_settings),
            rumps.MenuItem("Quit", callback=self.quit_app),
        ]

        if self.config.get("token") and self.config.get("gitlab_base_url"):
            self._start_background_refresh()
        else:
            self.title = "⬆ ⚠"
            missing = []
            if not self.config.get("gitlab_base_url"):
                missing.append("GitLab URL")
            if not self.config.get("token"):
                missing.append("token")
            rumps.notification(
                "GitLab Tracker",
                "Configuration Required",
                f"Please set your {' and '.join(missing)} in Settings.",
            )

    def _start_background_refresh(self):
        self._fetch_and_schedule_ui_update()
        interval = self.config.get("refresh_interval_seconds", 60)
        self._timer = rumps.Timer(self._timer_refresh, interval)
        self._timer.start()

    def _timer_refresh(self, _):
        thread = threading.Thread(target=self._fetch_and_schedule_ui_update, daemon=True)
        thread.start()

    def manual_refresh(self, _):
        thread = threading.Thread(target=self._fetch_and_schedule_ui_update, daemon=True)
        thread.start()

    def _fetch_and_schedule_ui_update(self):
        token = self.config.get("token", "")
        base_url = self.config.get("gitlab_base_url", "")
        if not token:
            return

        if not self.username:
            self.username = fetch_current_username(token, base_url)

        events = fetch_push_events(token, base_url)
        if events is None:
            self.error_state = True
            self.title = f"⬆ {self.push_count}!"
            return

        self.error_state = False
        self.events = events
        self.project_names = resolve_project_names(events, token, base_url)
        self.push_count, self.project_counts = count_pushes_today(events)
        self.last_update = datetime.now()

        self._cache_events(events)
        self._check_contribution_reminder()
        rumps.Timer(self._apply_ui_update, 0.1).start()

    def _apply_ui_update(self, timer):
        timer.stop()
        self._update_ui()

    def _check_contribution_reminder(self):
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        if now.hour >= 15 and self.push_count == 0 and self._reminder_shown_date != today:
            self._reminder_shown_date = today
            rumps.notification(
                "GitLab Tracker",
                "Contribution Reminder",
                "You have no pushes today. Time to contribute!",
            )

    def _cache_events(self, events):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, "w") as f:
                json.dump({"timestamp": time.time(), "events": events}, f)
        except OSError:
            pass

    def _update_ui(self):
        color_indicator = self._activity_indicator(self.push_count)
        self.title = f"{color_indicator} {self.push_count}"

        for key, item in self.menu.items():
            if not hasattr(item, "title"):
                continue
            if item.title.startswith("Today's Pushes"):
                item.title = f"Today's Pushes: {self.push_count}"
            elif item.title.startswith("Last update"):
                if self.last_update:
                    item.title = f"Last update: {self.last_update.strftime('%H:%M:%S')}"

        for old_key in self._project_keys:
            try:
                del self.menu[old_key]
            except KeyError:
                pass
        self._project_keys = []

        if self.project_counts:
            sorted_projects = sorted(self.project_counts.items(), key=lambda x: x[1], reverse=True)
            anchor = "Today's Pushes: -"

            for pid, count in sorted_projects:
                name = self.project_names.get(pid, str(pid))
                short_name = name.split("/")[-1] if "/" in name else name
                label = f"  {short_name}: {count} push"
                self._project_keys.append(label)
                project_url = f"{self.config.get('gitlab_base_url', '')}/{name}"
                item = rumps.MenuItem(label, callback=self._make_open_url(project_url))
                self.menu.insert_after(anchor, item)
                anchor = label

    def open_profile(self, _):
        base_url = self.config.get("gitlab_base_url", "")
        if self.username:
            webbrowser.open(f"{base_url}/{self.username}")
        else:
            webbrowser.open(base_url)

    def _make_open_url(self, url):
        def callback(_):
            webbrowser.open(url)
        return callback

    def _activity_indicator(self, count):
        if count == 0:
            return "⬆"
        elif count < 10:
            return "🟦"
        elif count < 20:
            return "🟩"
        elif count < 30:
            return "🟧"
        else:
            return "🟥"

    def open_settings(self, _):
        url_response = rumps.Window(
            title="GitLab Base URL",
            message="Enter your GitLab instance URL (e.g. https://gitlab.example.com):",
            default_text=self.config.get("gitlab_base_url", ""),
            ok="Next",
            cancel="Cancel",
        ).run()

        if not url_response.clicked:
            return

        token_response = rumps.Window(
            title="GitLab Token",
            message="Enter your GitLab Private Access Token:",
            default_text=self.config.get("token", ""),
            ok="Save",
            cancel="Cancel",
        ).run()

        if not token_response.clicked:
            return

        new_url = url_response.text.strip().rstrip("/")
        new_token = token_response.text.strip()
        changed = False

        if new_url and new_url != self.config.get("gitlab_base_url"):
            self.config["gitlab_base_url"] = new_url
            self.username = None
            changed = True
        if new_token and new_token != self.config.get("token"):
            self.config["token"] = new_token
            self.username = None
            changed = True

        if changed:
            save_config(self.config)

        if self.config.get("token") and self.config.get("gitlab_base_url"):
            if not hasattr(self, "_timer") or not self._timer.is_alive():
                self._start_background_refresh()
            elif changed:
                self._fetch_and_schedule_ui_update()

    def quit_app(self, _):
        rumps.quit_application()


def main():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
    app = GitLabTracker()
    app.run()


if __name__ == "__main__":
    main()
