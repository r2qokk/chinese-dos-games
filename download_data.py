import asyncio
import hashlib
import json
from collections import namedtuple
from pathlib import Path
from urllib.parse import quote, urljoin
from urllib.request import urlopen

ROOT = Path(__name__).resolve().parent
INFO = ROOT.joinpath('games.json')
DESTINATION = ROOT.joinpath('bin')
BASE = 'https://dos.zczc.cz/static/games/bin/'
GAME_INFO = namedtuple('GAME_INFO', ['name', 'file_location', 'url', 'hash_value'])


async def is_download_needed(info):
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


async def unit_of_work(info):
    name = info.name
    # TODO curses
    print('   checking %(name)-20s' % {'name': name}, end='\r')
    if await is_download_needed(info):
        print('downloading %(name)-20s' % {'name': name}, end='\r')
        await download(info)
        print('done with   %(name)-20s' % {'name': name}, end='\r')
    else:
        print('done with   %(name)-20s' % {'name': name}, end='\r')


def main(info):
    """
    check game archives whether exists and their checksum, download from target.
    """
    tasks = (unit_of_work(info_) for info_ in info)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*tasks))
    loop.close()
    print('Game on!')


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

    main(info)
