import os
from hashlib import sha256
from pathlib import Path

from aiofile import async_open
from structlog.stdlib import get_logger
from vyper import v

from competition_api.file_folder_copy import copy_file

v.set_default("flatfile_dir", f"{os.environ['AIXCC_CRS_SCRATCH_SPACE']}/vapi_flatfiles")
LOGGER = get_logger(__name__)


FLATFILE_TEMP_DIR = Path('/tmp')


class Flatfile:
    def __init__(
        self,
        contents: bytes | None = None,
        contents_hash: str | None = None,
    ):
        self.directory = Path(v.get("flatfile_dir"))
        self.directory.mkdir(exist_ok=True)
        self._contents = contents

        if self._contents:
            self.sha256 = sha256(self._contents).hexdigest()
        elif contents_hash:
            self.sha256 = contents_hash
        else:
            raise ValueError("Flatfile needs either contents or a hash to look up")

        self.filename = self.directory / self.sha256

        if contents_hash and not os.path.isfile(self.filename):
            raise ValueError("Supplied hash does not map to a real file on disk")

    async def write(self):

        # To ensure correct behavior in the /crs_scratch environment,
        # write to /tmp/<filename> and rsync it into the actual
        # flatfiles directory, instead of writing directly

        temp_path = FLATFILE_TEMP_DIR / self.filename.name

        await LOGGER.adebug(
            "Writing %s bytes to %s via %s", len(self._contents or ""), self.filename, temp_path
        )

        async with async_open(temp_path, "wb") as f:
            await f.write(self._contents)

        copy_file(temp_path, self.filename)

        temp_path.unlink()

    async def read(self) -> bytes | None:
        await LOGGER.adebug("Reading content of %s", self.filename)
        async with async_open(self.filename, "rb") as f:
            self._contents = await f.read()
            return self._contents
