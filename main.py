import argparse
import asyncio
from datetime import datetime, timedelta
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess

import aiohttp
from platformdirs import PlatformDirs
from endpoints import Endpoints
import aiofiles

from mdl.author_profile import AProfile
from mdl.settings import Settings

class PawchiveHooker(Endpoints):
    def __init__(self, timeout: int = 10, semaphore: int = 4, autoUpdate: bool = False):
        super().__init__()
        self.semaphore = semaphore
        self.timeout = timeout

        self.CONFIGS = PlatformDirs('Pawchive', ensure_exists=True).user_config_path
        self.BASE_DIR = Path(__file__).resolve().parent
        self.SETTINGS_DIR = self.CONFIGS / 'settings'
        Path.mkdir(self.SETTINGS_DIR, exist_ok=True)
        self.authors_file = self.SETTINGS_DIR / 'authors.txt'
        self.settings_file = self.SETTINGS_DIR / 'settings.json'
        if not self.authors_file.exists():
            self.authors_file.write_text('')
        self.AUTHORS_DIR = self.CONFIGS / 'hooked_data'
        Path.mkdir(self.AUTHORS_DIR, exist_ok=True)

    async def update_url(self):
        url = 'https://raw.githubusercontent.com/MetyV/PawchiveHooker/main/endpoints.py'
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(self.timeout)) as s:
            async with s.get(url) as r:
                if r.status == 200:
                    c = await r.read()
                    async with aiofiles.open(self.BASE_DIR/'endpoints.py', 'wb') as f:
                        await f.write(c)

    def get_authors(self):
        authors = []
        with open(self.authors_file, 'r', encoding='utf-8') as f:
            for _, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('|')
                if len(parts) != 2:
                    continue
                service = parts[0].strip()
                id = parts[1].strip()
                if not service or not id:
                    continue
                authors.append((service, id))
        return authors

    def add_user(self, service, id):
        with self.authors_file.open('a', encoding='utf-8') as f:
            f.write(f'{service}|{id}\n')

    async def get_author_update_data(self, service, id):
        url = self.BASE_API + f'/{service}/user/{id}/profile'
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(self.timeout)) as s:
            async with s.get(url) as r:
                if not r.status == 200:
                    return
                data = await r.json()
        if not data:
            print('No author data')
            return
        data = AProfile.model_validate(data)
        name = data.name
        safe = ''.join(c for c in name if c.isalnum() or c in '-_.') or f'{service}_{id}'
        author = self.AUTHORS_DIR / f'{safe}.json'
        if not author.exists():
            author.write_text(data.model_dump_json(indent=2), encoding='utf-8')
            return
        ttime = AProfile.model_validate_json(author.read_text(encoding='utf-8')).updated
        time = data.updated
        if not time > ttime:
            return
        
        author.write_text(data.model_dump_json(indent=2), encoding='utf-8')
        self.notify('Author updated', name)
        return True

    def notify(self, title: str, message: str):
        system = platform.system()

        try:
            if system == 'Linux':
                self._notify_linux(title, message)
            elif system == 'Darwin':
                self._notify_macos(title, message)
            elif system == 'Windows':
                self._notify_windows(title, message)
        except Exception as e:
            print(f'Notify failed: {e}')

    def _notify_linux(self, title: str, message: str): # work on kde and gnome, about others idk
        if not shutil.which('notify-send'):
            print(f'[{title}] {message}')
            return
        subprocess.run(
            ['notify-send', title, message],
            check=False,
            timeout=5,
        )

    def _notify_macos(self, title: str, message: str): # may not work.  AI CODE, I DON'T USE MACOS!!!
        script = f'display notification "{message}" with title "{title}"'
        subprocess.run(
            ['osascript', '-e', script],
            check=False,
            timeout=5,
        )

    def _notify_windows(self, title: str, message: str): # may not work.  AI CODE, I DON'T USE WINDOWS!!!
        ps = (
            '[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null;'
            '$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent('
            '[Windows.UI.Notifications.ToastTemplateType]::ToastText02);'
            "$text = $template.GetElementsByTagName('text');"
            f"$text.Item(0).AppendChild($template.CreateTextNode('{title}')) > $null;"
            f"$text.Item(1).AppendChild($template.CreateTextNode('{message}')) > $null;"
            '$toast = [Windows.UI.Notifications.ToastNotification]::new($template);'
            "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Pawchive').Show($toast);"
        )
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        subprocess.run(
            ['powershell', '-NoProfile', '-Command', ps],
            check=False,
            timeout=10,
            creationflags=flags,
        )

    def load_settings(self) -> Settings:
        if self.settings_file.exists():
            self.settings = Settings.model_validate_json(
                self.settings_file.read_text(encoding='utf-8')
            )
        else:
            self.settings = Settings()
            self.save_settings()
        return self.settings

    def save_settings(self):
        self.settings_file.write_text(
            self.settings.model_dump_json(indent=2),
            encoding='utf-8',
        )

async def checker(hooker: PawchiveHooker, profiles: bool, posts: bool):
    authors = hooker.get_authors()
    if not authors:
        return

    sem = asyncio.Semaphore(hooker.settings.semaphore)

    async def fetch(service, id):
        async with sem:
            if profiles:
                await hooker.get_author_update_data(service, id)
            if posts:
                pass
                #await hooker.get_author_posts_data(service, id)

    await asyncio.gather(
        *(fetch(s, i) for s, i in authors),
        return_exceptions=True,
    )

def sunh() -> float:
    now = datetime.now()
    next_run = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return (next_run - now).total_seconds()

async def looper(hooker: PawchiveHooker, *, profiles: bool, posts: bool):
    while True:
        hooker.load_settings()
        try:
            await checker(hooker, profiles, posts)
        except Exception as e:
            print(f'Error: {e}')
        delay = sunh()
        await asyncio.sleep(delay)
        
def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('--add-author', help='service:id')
    parser.add_argument('--semaphore', type=int, default=None)
    parser.add_argument('--check-profiles', action='store_true', default=False)
    parser.add_argument('--check-posts', action='store_true', default=False)
    parser.add_argument('--auto-update', action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument('action', choices=['start', 'stop'])

    args = parser.parse_args()

    hooker = PawchiveHooker()
    if args.add_author:
        if '|' not in args.add_author:
            print('Format: service|id')
            return
        service, id = args.add_author.split('|', 1)
        hooker.add_user(service.strip(), id.strip())
        print(f'Added: {service}|{id}')
    hooker.load_settings()

    if args.semaphore is not None:
        hooker.settings.semaphore = args.semaphore
    if args.auto_update is not None:
        hooker.settings.auto_update = args.auto_update
    hooker.save_settings()

    pid_file = hooker.CONFIGS / 'hooker.pid'

    if args.action == 'start':
        if pid_file.exists():
            print(f'(pid={pid_file.read_text().strip()})')
            return
        if hooker.settings.auto_update:
            asyncio.run(hooker.update_url())
        pid_file.write_text(str(os.getpid()))
        try:
            asyncio.run(looper(hooker, profiles=args.check_profiles, posts=args.check_posts))
        finally:
            pid_file.unlink(missing_ok=True)

    elif args.action == 'stop':
        if not pid_file.exists():
            print('No pid')
            return
        pid = int(pid_file.read_text().strip())
        try:
            os.kill(pid, signal.SIGTERM)
            print(f'Stopped pid={pid}')
        except ProcessLookupError:
            print(f'Pid {pid} not found')
        finally:
            pid_file.unlink(missing_ok=True)

if __name__ == '__main__':
    cli()