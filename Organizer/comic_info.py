import copy
import json
import logging
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from .comic_format import ComicFormat
from .comic_genre import ComicGenre
from .console import Console
from .utils import get_enum_title, remove_annoying_chars, yaml_setup

LOGGER = logging.getLogger(__name__)
DEFAULT_INFO = {
    'Publisher': None,
    'Series': {
        'Title': None,
        'Volume': 1
    },
    'Comic': {
        'Number': None,
        'Title': None
    },
    'Variant': False,
    'Summary': None,
    'Cover Date': None,
    'Language': 'EN',
    'Format': ComicFormat.COMIC,
    'Genres': [],
    'Page Count': 1,
    'Creators': {},
    'Alternative Series': [],
    'Identifiers': {},
    'Notes': None
}


def load_comic_info(folder: Path) -> Dict[str, Any]:
    json_file = folder.joinpath('ComicInfo.json')
    yaml_file = folder.joinpath('ComicInfo.yaml')
    xml_file = folder.joinpath('ComicInfo.xml')
    if json_file.exists():
        return __load_json_info(json_file)
    if yaml_file.exists():
        return __load_yaml_info(yaml_file)
    elif xml_file.exists():
        comic_info = __load_xml_info(xml_file)
        xml_file.unlink(missing_ok=True)
        format_option = Console.display_menu([get_enum_title(x) for x in ComicFormat], prompt='Select Format')
        comic_info['Format'] = list(ComicFormat)[format_option - 1]
        return comic_info
    comic_info = copy.deepcopy(DEFAULT_INFO)
    format_option = Console.display_menu([get_enum_title(x) for x in ComicFormat], prompt='Select Format')
    comic_info['Format'] = list(ComicFormat)[format_option - 1]
    return comic_info


def __load_xml_info(xml_file: Path) -> Dict[str, Any]:
    def str_to_list(soup, key: str) -> List[str]:
        return [x.strip() for x in (str(soup.find(key).string) if soup.find(key) else '').split(',') if x]

    comic_info = copy.deepcopy(DEFAULT_INFO)
    with open(xml_file, 'r', encoding='UTF-8') as xml_info:
        soup = BeautifulSoup(xml_info, 'xml')
        info = soup.find_all('ComicInfo')[0]
        LOGGER.debug(f"Loaded `{xml_file.name}`")

        comic_info['Publisher'] = str(info.find('Publisher').string) if info.find('Publisher') else None
        comic_info['Series']['Title'] = str(info.find('Series').string) if info.find('Series') else None
        comic_info['Series']['Volume'] = str(info.find('Volume').string) if info.find('Volume') else None
        comic_info['Comic']['Number'] = str(info.find('Number').string) if info.find('Number') else None
        # TODO: Read Comic Title from xml
        # region Alternative Series
        # Alternative Series - Title
        # Alternative Series - Volume
        # Alternative Series - Number
        # endregion
        comic_info['Summary'] = remove_annoying_chars(str(info.find('Summary').string)) \
            if info.find('Summary') else None
        year = int(info.find('Year').string) if info.find('Year') else None
        month = int(info.find('Month').string) if info.find('Month') else 1 if year else None
        day = int(info.find('Day').string) if info.find('Day') else 1 if month else None
        comic_info['Cover Date'] = date(year, month, day).isoformat() if year else None
        # region Creators
        roles = ['Artist', 'Writer', 'Penciller', 'Inker', 'Colourist', 'Colorist', 'Letterer', 'CoverArtist', 'Editor']
        for role in roles:
            creators = str_to_list(info, role)
            if creators:
                comic_info['Creators'][role] = creators
        # endregion
        comic_info['Genres'] = [x for x in [ComicGenre.from_string(x) for x in str_to_list(info, 'Genre')] if x]
        comic_info['Language'] = str(info.find('LanguageISO').string).upper() if info.find('LanguageISO') else None
        # TODO: Read Format from xml
        comic_info['Page Count'] = int(info.find('PageCount').string) if info.find('PageCount') else 0
        # TODO: Read Variant details from xml
        # region Identifiers
        if info.find('Web') and 'comixology' in str(info.find('Web').string).lower():
            comic_info['Identifiers']['Comixology'] = {
                'Url': str(info.find('Web').string),
                'Id': None
            }
        # endregion
        comic_info['Notes'] = remove_annoying_chars(str(info.find('Notes').string)) if info.find('Notes') else None

    return comic_info


def __load_json_info(json_file: Path) -> Dict[str, Any]:
    with open(json_file, 'r', encoding='UTF-8') as json_info:
        comic_info = json.load(json_info)
        comic_info['Format'] = ComicFormat.from_string(comic_info['Format']) or ComicFormat.COMIC
        comic_info['Genres'] = [x for x in [ComicGenre.from_string(x) for x in comic_info['Genres'].copy()] if x]
        return _validate_dict(comic_info)


def __load_yaml_info(yaml_file: Path) -> Dict[str, Any]:
    with open(yaml_file, 'r', encoding='UTF-8') as yaml_info:
        comic_info = yaml_setup().load(yaml_info)['Comic Info']
        comic_info['Series']['Volume'] = comic_info['Series']['Volume'] or 1
        comic_info['Series']['Title'] = comic_info['Series']['Name']
        del comic_info['Series']['Name']
        comic_info['Comic']['Number'] = comic_info['Comic']['Number'] or '1'
        comic_info['Format'] = ComicFormat.from_string(comic_info['Format']) or ComicFormat.COMIC
        comic_info['Genres'] = [x for x in [ComicGenre.from_string(x) for x in comic_info['Genres'].copy()] if x]
        comic_info['Cover Date'] = comic_info['Comic']['Release Date']
        del comic_info['Comic']['Release Date']
        comic_info['Language'] = comic_info['Language ISO'] or 'EN'
        del comic_info['Language ISO']
        for web, _id in comic_info['Identifiers'].copy().items():
            del comic_info['Identifiers'][web]
            if _id:
                comic_info['Identifiers'][web] = {
                    'Id': str(_id),
                    'Url': None
                }
        creators_dict = {}
        for creator in comic_info['Creators']:
            for role in creator['Role']:
                if role in creators_dict:
                    creators_dict[role].append(creator['Name'])
                else:
                    creators_dict[role] = [creator['Name']]
        del comic_info['Creators']
        comic_info['Creators'] = creators_dict
        return _validate_dict(comic_info)


def _validate_dict(mapping: Dict[str, Any]) -> Dict[str, Any]:
    temp_dict = copy.deepcopy(DEFAULT_INFO)
    for key, value in temp_dict.items():
        if key not in mapping:
            mapping[key] = value
        elif isinstance(value, dict):
            for sub_key, sub_value in value.items():
                if sub_key not in mapping[key]:
                    mapping[key][sub_key] = sub_value
    temp_dict = copy.deepcopy(mapping)
    for key, value in temp_dict.items():
        if key not in DEFAULT_INFO:
            mapping.pop(key, None)
        elif isinstance(value, dict) and key not in ['Identifiers', 'Creators']:
            for sub_key, sub_value in value.items():
                if sub_key not in DEFAULT_INFO[key]:
                    mapping[key].pop(sub_key, None)
    return mapping


def add_manual_info(comic_info: Dict[str, Any]) -> Dict[str, Any]:
    def str_entry(prompt: str, mapping: Dict[str, Any], key: str, default: Optional[str] = None):
        input_value = Console.display_prompt(f"{prompt} [{mapping[key]}]")
        if input_value == '**NONE**':
            mapping[key] = default
        elif input_value:
            mapping[key] = input_value

    def date_entry(prompt: str, mapping: Dict[str, Any], key: str, default: Optional[date] = None):
        input_value = Console.display_prompt(f"{prompt} (yyyy-mm-dd) [{mapping[key]}]")
        if input_value == '**NONE**':
            mapping[key] = default
        elif input_value:
            mapping[key] = datetime.strptime(input_value, '%Y-%m-%d').date()

    def int_entry(prompt: str, mapping: Dict[str, Any], key: str, default: int = 1):
        input_value = Console.display_prompt(f"{prompt} [{mapping[key]}]")
        if input_value == '**NONE**':
            mapping[key] = default
        elif input_value:
            try:
                mapping[key] = int(input_value)
            except ValueError:
                pass

    def enum_entry(prompt: str, mapping: Dict[str, Any], key: str, options: List[Enum], default: Optional[Any] = None):
        selected = Console.display_menu(prompt=f"{prompt} [{mapping[key]}]", items=[x.name for x in options],
                                        exit_text=default or '**NONE**')
        if selected:
            mapping[key] = options[selected - 1]
        elif default:
            mapping[key] = default
        else:
            mapping[key] = None

    str_entry('Publisher', comic_info, 'Publisher')
    str_entry('Series Title', comic_info['Series'], 'Title')
    int_entry('Series Volume', comic_info['Series'], 'Volume')
    str_entry('Comic Number', comic_info['Comic'], 'Number', '1')
    str_entry('Comic Title', comic_info['Comic'], 'Title')
    str_entry('Variant', comic_info, 'Variant')
    str_entry('Summary', comic_info, 'Summary')
    date_entry('Cover Date', comic_info, 'Cover Date')
    str_entry('Language', comic_info, 'Language', 'EN')
    str_entry('Summary', comic_info, 'Summary')
    enum_entry('Format', comic_info, 'Format', list(ComicFormat), ComicFormat.COMIC)
    LOGGER.warning('Unable to manually edit Lists, will need to do it via the ComicInfo file: Genres')
    int_entry('Page Count', comic_info, 'Page Count')
    LOGGER.warning('Unable to manually edit Lists, will need to do it via the ComicInfo file: Creators')
    LOGGER.warning('Unable to manually edit Lists, will need to do it via the ComicInfo file: Alternative Series')
    LOGGER.warning('Unable to manually edit Lists, will need to do it via the ComicInfo file: Identifiers')
    str_entry('Notes', comic_info, 'Notes')
    return comic_info


def save_comic_info(folder: Path, comic_info: Dict[str, Any], use_yaml: bool = False):
    comic_info['Genres'] = [get_enum_title(x) for x in comic_info['Genres']]
    comic_info['Format'] = get_enum_title(comic_info['Format'])
    if use_yaml:
        __save_yaml_info(folder, comic_info)
    else:
        __save_json_info(folder, comic_info)


def __save_json_info(folder: Path, comic_info: Dict[str, Any]):
    json_file = folder.joinpath('ComicInfo.json')
    if not json_file.exists():
        json_file.touch()
    comic_info['Genres'] = sorted(comic_info['Genres'])
    for key, value in comic_info['Creators'].copy().items():
        comic_info['Creators'][key] = sorted(comic_info['Creators'][key])
    comic_info['Alternative Series'] = sorted(comic_info['Alternative Series'],
                                              key=lambda x: (x['Title'], x['Volume'], x['Number']))
    comic_info['Identifiers'] = dict(sorted(comic_info['Identifiers'].items()))
    with open(json_file, 'w', encoding='UTF-8') as file_stream:
        json.dump(comic_info, file_stream, default=str, indent=2, ensure_ascii=False)


def __save_yaml_info(folder: Path, comic_info: Dict[str, Any]):
    yaml_file = folder.joinpath('ComicInfo.yaml')
    if not yaml_file.exists():
        yaml_file.touch()
    with open(yaml_file, 'w', encoding='UTF-8') as info_yaml:
        yaml_setup().dump({'Comic Info': comic_info}, info_yaml)