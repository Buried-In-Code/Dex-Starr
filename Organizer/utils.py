import logging
import re
from configparser import ConfigParser
from pathlib import Path
from typing import Tuple, List

from .comic_format import ComicFormat

LOGGER = logging.getLogger(__name__)
TOP_DIR = Path(__file__).resolve().parent.parent

CONFIG = ConfigParser(allow_no_value=True)
CONFIG.read('config.ini')
# General
ROOT_FOLDER = Path(CONFIG['General']['Root']).resolve()
ROOT_FOLDER.mkdir(parents=True, exist_ok=True)

PROCESSING_FOLDER = ROOT_FOLDER.joinpath('Processing')
PROCESSING_FOLDER.mkdir(parents=True, exist_ok=True)

COLLECTION_FOLDER = ROOT_FOLDER.joinpath('Collection')
COLLECTION_FOLDER.mkdir(parents=True, exist_ok=True)

# Comicvine
COMICVINE_API_KEY = CONFIG['Comicvine']['API Key']

# League of Comic Geeks
LOCG_API_KEY = CONFIG['League of Comic Geeks']['API Key']
LOCG_CLIENT_ID = CONFIG['League of Comic Geeks']['Client ID']

# Metron
METRON_USERNAME = CONFIG['Metron']['Username']
METRON_PASSWORD = CONFIG['Metron']['Password']


def list_files(folder: Path, filter: Tuple[str, ...] = ()) -> List[Path]:
    files = []
    for file in folder.iterdir():
        if file.is_dir():
            files.extend(list_files(file, filter))
        elif file.suffix in filter:
            files.append(file)
    return files


def slugify(value: str) -> str:
    value = ' '.join(re.sub(r"[^a-zA-Z0-9\s\-]+", '', value.strip().lower()).replace('-', ' ').split())
    return value.title().replace(' ', '-')


def slugify_publisher(title: str) -> str:
    return slugify(title)


def slugify_series(title: str, volume: int) -> str:
    series_slug = slugify(title)
    if volume and volume != 1:
        series_slug += f"-v{volume}"
    return series_slug


def slugify_comic(series_slug: str, comic_format: str, number: str) -> str:
    if comic_format == ComicFormat.TRADE_PAPERBACK.get_title():
        comic_slug = f"{series_slug}-Vol.{number}-TP"
    elif comic_format == ComicFormat.HARDCOVER.get_title():
        comic_slug = f"{series_slug}-Vol.{number}-HC"
    elif comic_format == ComicFormat.ANNUAL.get_title():
        comic_slug = f"{series_slug}-Annual-#{number}"
    elif comic_format == ComicFormat.DIGITAL_CHAPTER.get_title():
        comic_slug = f"{series_slug}-Chapter-#{number}"
    else:
        comic_slug = f"{series_slug}-#{number}"
    return comic_slug
