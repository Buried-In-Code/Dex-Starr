__all__ = ["ComicInfo", "Page"]

from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, ClassVar

import xmltodict
from natsort import humansorted as sorted
from natsort import ns
from pydantic import Field, validator

from dex_starr.models import PascalModel, clean_contents, from_xml_list, to_xml_list
from dex_starr.models.comic_info.enums import AgeRating, ComicPageType, Manga, YesNo
from dex_starr.models.metadata.enums import Format, Genre, Role
from dex_starr.models.metadata.schema import Creator, Issue, Metadata, Publisher, Series, StoryArc


class Page(PascalModel):
    image: int = Field(alias="@Image")
    page_type: ComicPageType = Field(alias="@Type", default=ComicPageType.STORY)
    double_page: bool = Field(alias="@DoublePage", default=False)
    image_size: int = Field(alias="@ImageSize", default=0)
    key: Optional[str] = Field(alias="@Key", default=None)
    bookmark: Optional[str] = Field(alias="@Bookmark", default=None)
    image_width: Optional[int] = Field(alias="@ImageWidth", default=None)
    image_height: Optional[int] = Field(alias="@ImageHeight", default=None)

    @validator("page_type", pre=True)
    def page_type_to_enum(cls, v) -> ComicPageType:
        if isinstance(v, str):
            return ComicPageType.load(v)
        return v

    def __lt__(self, other):
        if not isinstance(other, Page):
            raise NotImplementedError()
        return self.image < other.image

    def __eq__(self, other):
        if not isinstance(other, Page):
            raise NotImplementedError()
        return self.image == other.image

    def __hash__(self):
        return hash((type(self), self.image))


class ComicInfo(PascalModel):
    title: Optional[str] = None
    series: Optional[str] = None
    number: Optional[str] = None
    count: Optional[int] = None
    volume: Optional[int] = None
    alternate_series: Optional[str] = None
    alternate_number: Optional[str] = None
    alternate_count: Optional[int] = None
    summary: Optional[str] = None
    notes: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None
    writer: Optional[str] = None
    penciller: Optional[str] = None
    inker: Optional[str] = None
    colorist: Optional[str] = None
    letterer: Optional[str] = None
    cover_artist: Optional[str] = None
    editor: Optional[str] = None
    publisher: Optional[str] = None
    imprint: Optional[str] = None
    genre: Optional[str] = None
    web: Optional[str] = None
    page_count: int = 0
    language_iso: Optional[str] = Field(alias="LanguageISO", default=None)
    format: Optional[str] = None
    black_and_white: YesNo = Field(default=YesNo.UNKNOWN)
    manga: Manga = Field(default=Manga.UNKNOWN)
    characters: Optional[str] = None
    teams: Optional[str] = None
    locations: Optional[str] = None
    scan_information: Optional[str] = None
    story_arc: Optional[str] = None
    series_group: Optional[str] = None
    age_rating: AgeRating = Field(default=AgeRating.UNKNOWN)
    pages: List[Page] = Field(default_factory=list)
    community_rating: Optional[float] = Field(default=None, ge=0, le=5)

    listable_fields: ClassVar[Dict[str, str]] = {"Pages": "Page"}

    def __init__(self, **data):
        from_xml_list(mappings=ComicInfo.listable_fields, content=data)
        super().__init__(**data)

    @validator("black_and_white", pre=True)
    def black_and_white_to_enum(cls, v) -> YesNo:
        if isinstance(v, str):
            return YesNo.load(v)
        return v

    @validator("manga", pre=True)
    def manga_to_enum(cls, v) -> Manga:
        if isinstance(v, str):
            return Manga.load(v)
        return v

    @validator("age_rating", pre=True)
    def age_rating_to_enum(cls, v) -> AgeRating:
        if isinstance(v, str):
            return AgeRating.load(v)
        return v

    @property
    def story_arc_list(self) -> List[str]:
        if not self.alternate_series and not self.story_arc:
            return []
        if not self.alternate_series:
            return sorted({x.strip() for x in self.story_arc.split(",")}, alg=ns.NA | ns.G)
        if not self.story_arc:
            return sorted({x.strip() for x in self.alternate_series.split(",")}, alg=ns.NA | ns.G)
        return sorted(
            {
                *[x.strip() for x in self.alternate_series.split(",")],
                *[x.strip() for x in self.story_arc.split(",")],
            },
            alg=ns.NA | ns.G,
        )

    @property
    def cover_date(self) -> Optional[date]:
        if not self.year:
            return None
        return date(self.year, self.month or 1, self.day or 1)

    @property
    def writer_list(self) -> List[str]:
        if not self.writer:
            return []
        return sorted({x.strip() for x in self.writer.split(",")}, alg=ns.NA | ns.G)

    @property
    def penciller_list(self) -> List[str]:
        if not self.penciller:
            return []
        return sorted({x.strip() for x in self.penciller.split(",")}, alg=ns.NA | ns.G)

    @property
    def inker_list(self) -> List[str]:
        if not self.inker:
            return []
        return sorted({x.strip() for x in self.inker.split(",")}, alg=ns.NA | ns.G)

    @property
    def colourist_list(self) -> List[str]:
        if not self.colorist:
            return []
        return sorted({x.strip() for x in self.colorist.split(",")}, alg=ns.NA | ns.G)

    @property
    def colorist_list(self) -> List[str]:
        return self.colourist_list

    @property
    def letterer_list(self) -> List[str]:
        if not self.letterer:
            return []
        return sorted({x.strip() for x in self.letterer.split(",")}, alg=ns.NA | ns.G)

    @property
    def cover_artist_list(self) -> List[str]:
        if not self.cover_artist:
            return []
        return sorted({x.strip() for x in self.cover_artist.split(",")}, alg=ns.NA | ns.G)

    @property
    def editor_list(self) -> List[str]:
        if not self.editor:
            return []
        return sorted({x.strip() for x in self.editor.split(",")}, alg=ns.NA | ns.G)

    @property
    def genre_list(self) -> List[str]:
        if not self.genre:
            return []
        return sorted({x.strip() for x in self.genre.split(",")}, alg=ns.NA | ns.G)

    @property
    def character_list(self) -> List[str]:
        if not self.characters:
            return []
        return sorted({x.strip() for x in self.characters.split(",")}, alg=ns.NA | ns.G)

    @property
    def team_list(self) -> List[str]:
        if not self.teams:
            return []
        return sorted({x.strip() for x in self.teams.split(",")}, alg=ns.NA | ns.G)

    @property
    def location_list(self) -> List[str]:
        if not self.locations:
            return []
        return sorted({x.strip() for x in self.locations.split(",")}, alg=ns.NA | ns.G)

    def to_metadata(self) -> Metadata:
        # region Parse Creators
        creators = {}
        creator_mappings = {
            Role.WRITER: self.writer_list,
            Role.PENCILLER: self.penciller_list,
            Role.INKER: self.inker_list,
            Role.COLOURIST: self.colourist_list,
            Role.LETTERER: self.letterer_list,
            Role.COVER_ARTIST: self.cover_artist_list,
            Role.EDITOR: self.editor_list,
        }
        for key, value in creator_mappings.items():
            for creator in value:
                if creator not in creators:
                    creators[creator] = []
                creators[creator].append(key)
        # endregion
        return Metadata(
            publisher=Publisher(
                imprint=self.imprint,
                # TODO: Sources
                title=self.publisher,
            ),
            series=Series(
                # TODO: Sources
                start_year=self.volume if self.volume and self.volume > 1900 else None,
                title=self.series,
                volume=self.volume if self.volume and self.volume < 1900 else 1,
            ),
            issue=Issue(
                characters=self.character_list,
                cover_date=self.cover_date,
                creators=sorted(
                    {
                        Creator(name=name, roles=sorted(roles, alg=ns.NA | ns.G))
                        for name, roles in creators.items()
                    },
                    alg=ns.NA | ns.G,
                ),
                format=Format.load(self.format),
                genres=sorted({Genre.load(x) for x in self.genre_list}, alg=ns.NA | ns.G),
                language=self.language_iso.lower() if self.language_iso else "en",
                locations=self.location_list,
                number=self.number,
                page_count=self.page_count,
                # TODO: Sources
                # TODO: Store date
                story_arcs=sorted(
                    {StoryArc(title=x) for x in self.story_arc_list}, alg=ns.NA | ns.G
                ),
                summary=self.summary,
                teams=self.team_list,
                title=self.title,
            ),
            pages=sorted(
                {
                    Page(
                        image=x.image,
                        page_type=x.page_type,
                        double_page=x.double_page,
                        image_size=x.image_size,
                        key=x.key,
                        bookmark=x.bookmark,
                        image_width=x.image_width,
                        image_height=x.image_height,
                    )
                    for x in self.pages
                },
                alg=ns.NA | ns.G,
            ),
            notes=self.notes,
        )

    @staticmethod
    def from_file(info_file: Path) -> "ComicInfo":
        with info_file.open("rb") as stream:
            content = xmltodict.parse(stream, force_list=list(ComicInfo.listable_fields.values()))["ComicInfo"]
            return ComicInfo(**content)

    def to_file(self, info_file: Path):
        content = self.dict(by_alias=True, exclude_none=True)
        to_xml_list(mappings=ComicInfo.listable_fields, content=content)
        content = clean_contents(content)

        with info_file.open("w", encoding="UTF-8") as stream:
            xmltodict.unparse(
                {"ComicInfo": {k: content[k] for k in sorted(content, alg=ns.NA | ns.G)}},
                output=stream,
                short_empty_elements=True,
                pretty=True,
            )
