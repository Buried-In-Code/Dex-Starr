__all__ = ["Archive"]

import shutil
from pathlib import Path
from typing import Optional
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from patoolib import extract_archive
from patoolib.util import PatoolError

from dex_starr import (
    SUPPORTED_FILE_EXTENSIONS,
    SUPPORTED_IMAGE_EXTENSIONS,
    SUPPORTED_INFO_FILES,
    get_cache_root,
    list_files,
)
from dex_starr.console import CONSOLE
from dex_starr.models.metadata.schema import Metadata
from dex_starr.settings import GeneralSettings


class Archive:
    def __init__(self, file: Path):
        self.source_file = file
        self.extracted_folder: Optional[Path] = None
        self.result_file: Optional[Path] = None

    def _extract_zip(self, extracted_folder: Path) -> bool:
        try:
            with ZipFile(self.source_file, "r") as stream:
                stream.extractall(path=extracted_folder)
            self.extracted_folder = extracted_folder
            return True
        except BadZipFile as err:
            CONSOLE.print(err, style="logging.level.error")
            return False

    def _extract_seven(self, extracted_folder: Path) -> bool:
        from py7zr import SevenZipFile

        with SevenZipFile(self.source_file, "r") as stream:
            stream.extractall(path=extracted_folder)
        self.extracted_folder = extracted_folder
        return True

    def _extract_archive(self, extracted_folder: Path) -> bool:
        try:
            output = extract_archive(
                self.source_file, outdir=extracted_folder, verbosity=-1, interactive=False
            )
            self.extracted_folder = Path(output)
            return True
        except PatoolError as err:
            CONSOLE.print(err, style="logging.level.error")
            return False

    def extract(self) -> bool:
        CONSOLE.print(f"Extracting {self.source_file.name}", style="logging.level.info")
        extracted_folder = get_cache_root() / self.source_file.stem
        if extracted_folder.exists():
            CONSOLE.print(
                f"{extracted_folder.name} already exists in {extracted_folder.parent.name}",
                style="logging.level.warning",
            )
            return False
        extracted_folder.mkdir(parents=True, exist_ok=True)

        if self.source_file.suffix == ".cbz":
            return self._extract_zip(extracted_folder)
        if self.source_file.suffix == ".cb7":
            return self._extract_seven(extracted_folder)
        if self.source_file.suffix in SUPPORTED_FILE_EXTENSIONS:
            return self._extract_archive(extracted_folder)
        CONSOLE.print(
            f"Unknown archive format given: {self.source_file.name}", style="logging.level.error"
        )
        return False

    def _rename_images(self):
        image_list = list_files(self.extracted_folder, filter_=SUPPORTED_IMAGE_EXTENSIONS)
        list_length = len(str(len(image_list)))
        for index, img_file in enumerate(image_list):
            img_file.rename(
                self.extracted_folder
                / f"{self.result_file.stem}-{str(index).zfill(list_length)}{img_file.suffix}"
            )

    def _archive_zip(self, archive_file: Path):
        with ZipFile(archive_file, "w", ZIP_DEFLATED) as stream:
            for file in list_files(self.extracted_folder):
                if file.suffix in SUPPORTED_IMAGE_EXTENSIONS:
                    stream.write(file, file.relative_to(self.extracted_folder))
                elif file.name in SUPPORTED_INFO_FILES:
                    stream.write(file, file.relative_to(self.extracted_folder))
                else:
                    CONSOLE.print(
                        f"Unsupported file found: {file.name}", style="logging.level.warning"
                    )

    def _archive_seven(self, archive_file: Path):
        from py7zr import SevenZipFile

        with SevenZipFile(archive_file, "w") as stream:
            for file in list_files(self.extracted_folder):
                if file.suffix in SUPPORTED_IMAGE_EXTENSIONS:
                    stream.write(file, file.relative_to(self.extracted_folder))
                elif file.name in SUPPORTED_INFO_FILES:
                    stream.write(file, file.relative_to(self.extracted_folder))
                else:
                    CONSOLE.print(
                        f"Unsupported file found: {file.name}", style="logging.level.warning"
                    )

    def archive(self, metadata: Metadata, general: GeneralSettings) -> bool:
        series_folder = (
            general.collection_folder / metadata.publisher.file_name / metadata.series.file_name
        )
        series_folder.mkdir(parents=True, exist_ok=True)
        self.result_file = (
            series_folder
            / f"{metadata.series.file_name}{metadata.issue.file_name}.{general.output_format}"
        )
        CONSOLE.print(f"Archiving {self.result_file.name}", style="logging.level.info")
        if self.result_file.exists():
            CONSOLE.print(f"{self.result_file.name} already exists", style="logging.level.error")
            return False
        self._rename_images()

        archive_file = self.extracted_folder.parent / self.result_file.name
        if archive_file.exists():
            return False

        try:
            if general.output_format == "cbz":
                self._archive_zip(archive_file)
            elif general.output_format == "cb7":
                self._archive_seven(archive_file)
            else:
                return False
        except OSError as err:
            CONSOLE.print(err, style="logging.level.error")
            return False

        return shutil.move(archive_file, self.result_file)
