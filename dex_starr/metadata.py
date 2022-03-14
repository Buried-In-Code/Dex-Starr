import json
from datetime import date
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional

import xmltodict
from jsonschema import ValidationError
from jsonschema import validate as validate_json
from rich import inspect
from rich.prompt import IntPrompt, Prompt
from yamale import YamaleError, make_data, make_schema
from yamale import validate as validate_yaml

from . import __version__
from .console import CONSOLE, create_menu
from .settings import SETTINGS


class FormatEnum(Enum):
    ANNUAL = auto()
    COMIC = auto()
    DIGITAL_CHAPTER = auto()
    HARDCOVER = auto()
    TRADE_PAPERBACK = auto()

    @staticmethod
    def select() -> "FormatEnum":
        options = [x.get_title() for x in sorted(FormatEnum)]
        selected = create_menu(prompt="Enter Format", options=options)
        return FormatEnum.get(name=options[selected]) or FormatEnum.COMIC

    @staticmethod
    def get(name: str) -> Optional["FormatEnum"]:
        for entry in FormatEnum:
            if entry.get_title().lower() == name.lower():
                return entry
        return None

    def get_title(self) -> str:
        return self.name.replace("_", " ").title()

    def __lt__(self, other):
        if not isinstance(other, FormatEnum):
            raise NotImplementedError()
        return self.name < other.name


class Identifier:
    def __init__(self, service: str, id_: Optional[int] = None, url: Optional[str] = None):
        self.service = service
        self.id_ = id_
        self.url = url

    @staticmethod
    def load(data: Dict[str, Any]) -> "Identifier":
        try:
            id_ = int(data["ID"])
        except TypeError:
            id_ = None
        return Identifier(service=data["Service"], id_=id_, url=data["URL"])

    def dump(self) -> Dict[str, Any]:
        return {"Service": self.service, "ID": self.id_, "URL": self.url}


class Publisher:
    def __init__(self, title: str):
        self.title = title
        self.identifiers: List[Identifier] = []

    @staticmethod
    def load(data: Dict[str, Any]) -> "Publisher":
        publisher = Publisher(title=data["Title"])

        publisher.identifiers = [Identifier.load(x) for x in data["Identifiers"]]

        return publisher

    def dump(self) -> Dict[str, Any]:
        return {
            "Title": self.title,
            "Identifiers": [x.dump() for x in self.identifiers],
        }

    def set_metadata(self, metadata: Dict[str, Any], resolve_manually: bool = False):
        if "title" in metadata:
            title = get_field(
                metadata=metadata,
                section="Publisher",
                field="title",
                order=[] if resolve_manually else SETTINGS.resolution_order,
            )
            if title:
                self.title = title


class Series:
    def __init__(self, title: str, volume: int = 1):
        self.title = title
        self.volume = volume
        self.identifiers: List[Identifier] = []
        self.start_year: Optional[int] = None

    @staticmethod
    def load(data: Dict[str, Any]) -> "Series":
        series = Series(title=data["Title"], volume=data["Volume"])

        series.identifiers = [Identifier.load(x) for x in data["Identifiers"]]
        series.start_year = data["Start Year"]

        return series

    def dump(self) -> Dict[str, Any]:
        if not self.start_year or self.start_year <= 1900:
            self.start_year = 1900
        return {
            "Title": self.title,
            "Volume": self.volume if self.volume >= 1 else 1,
            "Identifiers": [x.dump() for x in self.identifiers],
            "Start Year": self.start_year,
        }

    def set_metadata(self, metadata: Dict[str, Any], resolve_manually: bool = False):
        if "title" in metadata:
            title = get_field(
                metadata=metadata,
                section="Series",
                field="title",
                order=[] if resolve_manually else SETTINGS.resolution_order,
            )
            if title:
                self.title = title
        if "volume" in metadata:
            volume = get_field(
                metadata=metadata,
                section="Series",
                field="volume",
                order=[] if resolve_manually else SETTINGS.resolution_order,
            )
            if volume:
                self.volume = volume
        if "start_year" in metadata:
            start_year = get_field(
                metadata=metadata,
                section="Series",
                field="start_year",
                order=[] if resolve_manually else SETTINGS.resolution_order,
            )
            if start_year:
                self.start_year = start_year


class Creator:
    def __init__(self, name: str, roles: List[str]):
        self.name = name
        self.roles = roles

    @staticmethod
    def load(data: Dict[str, Any]) -> "Creator":
        creator = Creator(name=data["Name"], roles=data["Roles"])

        return creator

    def dump(self) -> Dict[str, Any]:
        return {"Name": self.name, "Roles": self.roles}


class Comic:
    def __init__(self, number: str, format_: FormatEnum = FormatEnum.COMIC):
        self.format_ = format_
        self.number = number

        self.cover_date: Optional[date] = None
        self.creators: List[Creator] = []
        self.genres: List[str] = []
        self.identifiers: List[Identifier] = []
        self.language_iso: Optional[str] = None
        self.page_count: Optional[int] = None
        self.store_date: Optional[date] = None
        self.summary: Optional[str] = None
        self.title: Optional[str] = None

    @staticmethod
    def load(data: Dict[str, Any]) -> "Comic":
        comic = Comic(
            format_=FormatEnum.get(data["Format"]) or FormatEnum.COMIC,
            number=data["Number"],
        )

        comic.cover_date = date.fromisoformat(data["Cover Date"]) if data["Cover Date"] else None
        comic.creators = [Creator.load(x) for x in data["Creators"]]
        comic.genres = data["Genres"]
        comic.identifiers = [Identifier.load(x) for x in data["Identifiers"]]
        comic.language_iso = data["Language ISO"]
        comic.page_count = data["Page Count"]
        comic.store_date = date.fromisoformat(data["Store Date"]) if data["Store Date"] else None
        comic.summary = data["Summary"]
        comic.title = data["Title"]

        return comic

    def dump(self) -> Dict[str, Any]:
        if not self.page_count or self.page_count <= 1:
            self.page_count = 1
        return {
            "Format": self.format_.get_title(),
            "Number": self.number,
            "Cover Date": self.cover_date.isoformat() if self.cover_date else None,
            "Creators": [x.dump() for x in self.creators],
            "Genres": self.genres,
            "Identifiers": [x.dump() for x in self.identifiers],
            "Language ISO": self.language_iso,
            "Page Count": self.page_count,
            "Store Date": self.store_date.isoformat() if self.store_date else None,
            "Summary": self.summary,
            "Title": self.title,
        }

    def set_metadata(self, metadata: Dict[str, Any], resolve_manually: bool = False):
        if "format" in metadata:
            format_ = get_field(
                metadata=metadata,
                section="Comic",
                field="format",
                order=[] if resolve_manually else SETTINGS.resolution_order,
            )
            if format_:
                self.format_ = format_
        if "number" in metadata:
            number = get_field(
                metadata=metadata,
                section="Comic",
                field="number",
                order=[] if resolve_manually else SETTINGS.resolution_order,
            )
            if number:
                self.number = number
        if "cover_date" in metadata:
            cover_date = get_field(
                metadata=metadata,
                section="Comic",
                field="cover_date",
                order=[] if resolve_manually else SETTINGS.resolution_order,
            )
            if cover_date:
                self.cover_date = cover_date
        # TODO: Creators
        # TODO: Genres
        if "page_count" in metadata:
            page_count = get_field(
                metadata=metadata,
                section="Comic",
                field="page_count",
                order=[] if resolve_manually else SETTINGS.resolution_order,
            )
            if page_count:
                self.page_count = page_count
        if "store_date" in metadata:
            store_date = get_field(
                metadata=metadata,
                section="Comic",
                field="store_date",
                order=[] if resolve_manually else SETTINGS.resolution_order,
            )
            if store_date:
                self.store_date = store_date
        if "summary" in metadata:
            summary = get_field(
                metadata=metadata,
                section="Comic",
                field="summary",
                order=[] if resolve_manually else SETTINGS.resolution_order,
            )
            if summary:
                self.summary = summary
        if "title" in metadata:
            title = get_field(
                metadata=metadata,
                section="Comic",
                field="title",
                order=[] if resolve_manually else SETTINGS.resolution_order,
            )
            if title:
                self.title = title


class Metadata:
    def __init__(
        self, publisher: Publisher, series: Series, comic: Comic, notes: Optional[str] = None
    ):
        self.publisher = publisher
        self.series = series
        self.comic = comic
        self.notes = notes

    @staticmethod
    def create() -> "Metadata":
        metadata = Metadata(
            publisher=Publisher(title=Prompt.ask("Publisher Title", console=CONSOLE)),
            series=Series(
                title=Prompt.ask("Series Title", console=CONSOLE),
                volume=IntPrompt.ask("Series Volume", default=1, console=CONSOLE),
            ),
            comic=Comic(
                format_=FormatEnum.select(),
                number=Prompt.ask("Issue Number", default="0", console=CONSOLE),
            ),
        )
        if (
            metadata.comic.format_ in [FormatEnum.TRADE_PAPERBACK, FormatEnum.HARDCOVER]
            and metadata.comic.number == "0"
        ):
            metadata.comic.title = Prompt.ask("Issue Title", console=CONSOLE) or None
        return metadata

    @staticmethod
    def load(data: Dict[str, Any]) -> "Metadata":
        return Metadata(
            publisher=Publisher.load(data["Data"]["Publisher"]),
            series=Series.load(data["Data"]["Series"]),
            comic=Comic.load(data["Data"]["Comic"]),
            notes=data["Meta"]["Notes"] if "Notes" in data["Meta"] else None,
        )

    def dump(self) -> Dict[str, Any]:
        output = {
            "Data": {
                "Publisher": self.publisher.dump(),
                "Series": self.series.dump(),
                "Comic": self.comic.dump(),
            },
            "Meta": {
                "Date": date.today().isoformat(),
                "Tool": {"Name": "Dex-Starr", "Version": __version__},
            },
        }
        if self.notes:
            output["Meta"]["Notes"] = self.notes
        return output

    def set_metadata(self, metadata: Dict[str, Any], resolve_manually: bool = False):
        self.publisher.set_metadata(
            metadata=metadata["publisher"], resolve_manually=resolve_manually
        )
        self.series.set_metadata(metadata=metadata["series"], resolve_manually=resolve_manually)
        self.comic.set_metadata(metadata=metadata["comic"], resolve_manually=resolve_manually)


def parse_yaml(info_file: Path) -> Optional[Metadata]:
    schema_file = Path("schemas").joinpath("ComicInfo.schema.yaml")
    data = make_data(content=info_file.read_text(encoding="UTF-8"), parser="ruamel")

    try:
        validate_yaml(
            make_schema(content=schema_file.read_text(encoding="UTF-8"), parser="ruamel"), data
        )
        return Metadata.load(data[0][0])
    except YamaleError as ye:
        inspect(data[0][0], title=ye.message, console=CONSOLE)
    return None


def parse_json(info_file: Path) -> Optional[Metadata]:
    schema_file = Path("schemas").joinpath("ComicInfo.schema.json")
    with schema_file.open("r", encoding="UTF-8") as schema_stream:
        schema_data = json.load(schema_stream)
    with info_file.open("r", encoding="UTF-8") as info_stream:
        info_data = json.load(info_stream)
    try:
        validate_json(instance=info_data, schema=schema_data)
        return Metadata.load(info_data)
    except ValidationError as ve:
        inspect(info_data, title=ve.message, console=CONSOLE)
    return None


def parse_xml(info_file: Path) -> Optional[Metadata]:
    with info_file.open("rb") as stream:
        data = xmltodict.parse(stream, dict_constructor=dict, xml_attribs=False)["ComicInfo"]

    year = int(data["Year"]) if "Year" in data else None
    month = int(data["Month"]) if "Month" in data else 1 if year else None
    day = int(data["Day"]) if "Day" in data else 1 if month else None

    creators = {}
    roles = [
        "Artist",
        "Writer",
        "Penciller",
        "Inker",
        "Colourist",
        "Colorist",
        "Letterer",
        "CoverArtist",
        "Editor",
    ]
    for role in roles:
        if role not in data:
            continue
        creator_str = data[role]
        if creator_str:
            role = "Cover Artist" if role == "CoverArtist" else role
            role = "Colourist" if role == "Colorist" else role
            creator_list = [x.strip() for x in creator_str.split(",")]
            for creator in creator_list:
                if creator in creators:
                    creators[creator]["Roles"].append(role)
                else:
                    creators[creator] = {"Name": creator, "Roles": [role]}

    if "Web" in data and data["Web"] and "comixology" in data["Web"].lower():
        identifier = [{"Service": "Comixology", "ID": None, "URL": data["Web"]}]
    else:
        identifier = []

    output = {
        "Publisher": {
            "Title": data["Publisher"]
            if "Publisher" in data
            else Prompt.ask("Publisher Title", console=CONSOLE),
            "Identifiers": [],
        },
        "Series": {
            "Title": data["Series"]
            if "Series" in data
            else Prompt.ask("Series Title", console=CONSOLE),
            "Volume": IntPrompt.ask("Series Volume", default=1, console=CONSOLE),
            "Identifiers": [],
            "Start Year": int(data["Volume"]) if "Volume" in data else None,
        },
        "Comic": {
            "Format": FormatEnum.select().get_title(),
            "Number": data["Number"]
            if "Number" in data
            else Prompt.ask("Issue Number", default="0", console=CONSOLE),
            "Cover Date": date(year, month, day).isoformat() if year else None,
            "Creators": list(creators.values()),
            "Genres": [x.strip() for x in data["Genre"].split(",")] if "Genre" in data else [],
            "Identifiers": identifier,
            "Language ISO": data["LanguageISO"].upper() if "LanguageISO" in data else None,
            "Page Count": int(data["PageCount"]) if "PageCount" in data else None,
            "Store Date": None,
            "Summary": data["Summary"] if "Summary" in data else None,
            "Title": None,
        },
    }
    if (
        output["Comic"]["Format"]
        in [FormatEnum.TRADE_PAPERBACK.get_title(), FormatEnum.HARDCOVER.get_title()]
        and output["Comic"]["Number"] == "0"
    ):
        output["Comic"]["Title"] = Prompt.ask("Issue Title", console=CONSOLE) or None

    return Metadata.load({"Data": output, "Meta": {}})


def get_field(
    metadata: Dict[str, Any], section: str, field: str, order: List[str] = None
) -> Optional[Any]:
    if not order:
        order = []
    if len(metadata[field]) == 1 or len(set(metadata[field].values())) == 1:
        return list(metadata[field].values())[0]
    if len(metadata[field]) > 1:
        if order:
            for entry in order:
                if entry in metadata[field]:
                    return metadata[field][entry]
        selected_index = create_menu(
            options=[f"{k} - {v}" for k, v in metadata[field].items()],
            prompt=f"Select {section} {field.replace('_', ' ').title()}",
        )
        return list(metadata[field].values())[selected_index - 1]
    return None