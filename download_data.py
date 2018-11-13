import asyncio
import curses
import hashlib
import json
from collections import namedtuple
from pathlib import Path
from urllib.parse import quote, urljoin
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
INFO = ROOT.joinpath('games.json')
DESTINATION = ROOT.joinpath('bin')
BASE = 'https://dos.zczc.cz/static/games/bin/'
GAME_INFO = namedtuple('GAME_INFO', ['name', 'file_location', 'url', 'hash_value'])


class Report:
    def __init__(self, screen, total):
        self._screen = screen
        self._total = total
        self._check = 0
        self._downloading = 0
        self._downloaded = 0
        self._done = 0

    def print_validate_progress(self):
        self._screen.addstr(0, 0,
                            'Checking: %(checking)5d / %(all)5d' %
                            {'checking': self._check, 'all': self._total})
        self._screen.refresh()

    def print_download_progress(self):
        self._screen.addstr(1, 0,
                            'Download: %(downloading)5d / %(all)5d' %
                            {'downloading': self._downloaded, 'all': self._downloading})
        self._screen.refresh()

    def print_overall_progress(self):
        self._screen.addstr(2, 0,
                            'Done: %(now)5d / %(all)5d' %
                            {'now': self._done, 'all': self._total})
        self._screen.refresh()

    def print_all_complete_message(self):
        self._screen.addstr(3, 0, 'Game on!')
        self._screen.refresh()

    def start_check(self):
        self._check += 1
        self.print_validate_progress()

    def start_download(self):
        self._downloading += 1
        self.print_download_progress()

    def downloaded(self):
        self._downloaded += 1
        self.print_download_progress()
        self.done()

    def done(self):
        self._done += 1
        self.print_overall_progress()

    def all_done(self):
        if self.done == self.total:
            self.print_all_complete_message()
        else:
            raise



def is_download_needed(info):
    location = info.file_location
    if location.is_file():
        sha256 = hashlib.sha256()
        with open(location, 'rb') as file:
            sha256.update(file.read())
        return info.hash_value != sha256.hexdigest()
    else:
        return True


async def download(info):
    response = await asyncio.get_event_loop().run_in_executor(None, urlopen, info.url)
    with open(info.file_location, 'wb', buffering=0) as file:
        file.write(response.read())


async def unit_of_work(info, reporter):
    """Check the intregrity of a game, and download it if needed."""
    reporter.start_check()
    if is_download_needed(info):
        reporter.start_download()
        await download(info)
        reporter.downloaded()
    else:
        reporter.done()


def main(info, reporter):
    tasks = (unit_of_work(info_, reporter) for info_ in info)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*tasks))
    loop.close()
    reporter.all_done()


if __name__ == '__main__':
    with open(INFO, encoding='utf8') as f:
        raw_info = json.load(f)

    destination = DESTINATION
    info = (GAME_INFO(name=name,
                      file_location=destination.joinpath(name).with_suffix('.zip'),
                      url=urljoin(BASE, quote(str(Path(name).with_suffix('.zip')))),
                      hash_value=raw_info['games'][name]['sha256'])
            for name in raw_info['games'])

    if not destination.is_dir():
        destination.mkdir()

    reporter = Report(curses.initscr(), len(raw_info['games']))
    curses.noecho()
    curses.cbreak()

    try:
        main(info, reporter)
    except Exception as e:
        raise e
    finally:
        curses.echo()
        curses.nocbreak()
        curses.endwin()
