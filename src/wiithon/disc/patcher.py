"""
Modifying a Wii disck image and rebuilding it

This module exposes :class:`WiiIsoPatcher`. To inspect it without modifying it, see :mod:`wiithon.disc.reader`
"""
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import Concatenate, ParamSpec, TypeVar, Optional

from wiithon.builder.copy_source import CopyPartitionSource
from wiithon.builder.disc_builder import WiiDiscBuilder
from wiithon.disc.enums import WiiPartType
from wiithon.disc.reader import WiiIsoReader
from wiithon.exceptions import NoDataPartitionError
from wiithon.formats.archive import Archive, Container, flush_archive_cache, resolve_read, resolve_write
from wiithon.disc.partition import WiiPartitionInfo

from wiithon import NoDataPartitionError
from wiithon.formats.bnr import BNR
from wiithon.formats.dol import DOL
from wiithon.fst.node import FSTFile
from wiithon.fst.operations import add_node, remove_node
from wiithon.fst.tree import FST

T = TypeVar("T")
P = ParamSpec("P")

class WiiIsoPatcher:
    """
    Collects modifications to a wii ISO and writes a new one

    Nothing is applied as you go. Every call records an intent and the whole set is replayed when :meth:`build` is called
    The source ISO is opened read only and never written to

    Warning:
        Only the DATA partition is patched. Other partition are copied to the output byte by byte

    Example:
        >>> with WiiIsoPatcher("path/to/iso") as patcher:
        ...     patcher.replace_file("opening.bnr", data)
        ...     patcher.modify_title("My super game")
        ...     patcher.build("output/iso")
    """
    def __init__(self, src_path: str) -> None:
        """
        Nothing is opened in the constructor

        Args:
            src_path: Path to the ISO file to patch. It's opened when entering in a ``with`` block
        """

        #: The source path
        self.src_path: str = src_path

        #: WiiIsoReader. Used internally
        self.reader: Optional[WiiIsoReader] = None

        #: The opened data partition
        self.data_partition: Optional[WiiPartitionInfo] = None # TODO: currently doing for data partition, may need a change

        #: A callback function that runs when build is called. Used for modifying the DOL
        self.dol_modifier: Optional[Callable[[DOL], None]] = None

        #: A dictionnary that map files to their data
        self.file_replacements: dict[str, bytes] = {}

        #: Callback applied to the FST at build time, set by :meth:`modify_fst`
        self.fst_modifier: Optional[Callable[[FST], None]] = None

        #: A dictionnary that map new files to their data
        self.files_to_add: dict[str, bytes] = {}

        #: A list of files to remove
        self.files_to_remove: list[str] = []

        self.cached_archive: tuple[str, Archive, list[Container]] | None = None

    def __enter__(self) -> "WiiIsoPatcher":
        """
        Open the source ISO and load its DATA partition

        Raises:
            NoDataPartitionError: If the disc has no DATA partition, which means
                there is nothing to patch
            InvalidDiscError: If the source is not a valid Wii disc image
        """
        self.reader = WiiIsoReader(self.src_path)
        try:
            self.reader.__enter__()
            entry = self.reader.get_data_partition()
            if entry is None:
                raise NoDataPartitionError(f"No DATA partition in {self.src_path}")

            self.data_partition = self.reader.open_partition(entry)

        except BaseException:
            self.reader.close()
            self.reader = None
            raise

        return self

    def __exit__(self, *args: int) -> None:
        if self.reader:
            self.reader.__exit__(*args)

    def modify_fst(self, fn: Callable[[FST], None]) -> None:
        """
        Register a callback that edits the file system table directly

        The callback runs during :meth:`build`, before the additions and removals queued by :meth:`add_file` and
        :meth:`remove_file` are applied

        Args:
            fn: Called with the FST of the DATA partition. Its return value is
                ignored, modify the tree in place

        Note:
            Only one callback is kept. Calling this twice replaces the first

        Example:
            >>> with WiiIsoPatcher("path/to/iso") as patcher:
            ...     patcher.modify_fst(lambda x: print(x.count_files()))
            ...     patcher.build("output")
        """
        self.fst_modifier = fn

    def add_file(self, path: str, data: bytes) -> None:
        """
        Queue a new file for insertion

        The file is added to the file system table and its data is written at build time. Parent directories must exists

        Args:
            path: Destination path inside the DATA partition. Leading and trailing slashes are stripped
            data: File content in bytes
        """
        key = path.strip("/")
        self.files_to_add[key] = data
        self.file_replacements[key] = data

    def remove_file(self, path: str) -> None:
        """
        Queue a new file for deletion

        If ``path`` was queued by :meth:`add_file` earlier that pending addition is cancelled instead of scheduling a removal

        Args:
            path: Destination path inside the DATA partition. Leading and trailing slashes are stripped

        Note:
            Removing a path that does not exist just do  nothing, since the FST finds nothing
        """
        key = path.strip("/")
        if key in self.files_to_add:
            self.files_to_add.pop(key)
            self.file_replacements.pop(key)
        else:
            self.files_to_remove.append(key)

    def replace_file(self, path: str, data: bytes) -> None:
        """
        Queue new contents for an existing file

        Unlike :meth:`add_file`, this does not touch the file system table, so the
        file must already exist on the disc. The new data may be of any size

        Args:
            path: Path inside the DATA partition
            data: Replacement contents
        """
        self.file_replacements[path.strip("/")] = data

    def list_files(self) -> list[str]:
        """
        List every file of the DATA partition

        Returns:
            Full paths, using ``/`` as separator

        Warning:
            This reflects the **source** disc. Files queued by :meth:`add_file` or
            :meth:`remove_file` do not appear or disappear until :meth:`build`
        """
        return self.data_partition.list_files()

    def read_file(self, path: str) -> bytes:
        """
        Read a file from the source disc

        Args:
            path: Path inside the DATA partition

        Returns:
            The contents as stored in the **source** ISO. Pending replacements are not applied,
            so reading a file you just replaced returns the original data

        Raises:
            FstFileNotFoundError: If no such file exists
            FstIsADirectoryError: If the path is a directory
        """
        return self.data_partition.read_file(path)

    @contextmanager
    def edit_as(self, path: str, cls: type[T], **kwargs: int) -> Iterator[T]:
        """
        Edit a file in place parsed as a given format

        Reads the file, parses it with ``cls.read()``, hands you the object, then serialises it back with
        ``obj.write()`` and queues the result as a replacement when the block exits

        The path may cross archive boundaries
        Given ``"Stage.arc/scenariodata.bcsv"``, the RARC archive is opened, the inner file is extracted,
        and the archive is re-serialised around your changes
        Yaz0 compression is handled transparently. Everything is transparent. You want the object, you have the object

        Args:
            path: Path inside the DATA partition, optionally continuing inside an archive
            cls: Format class providing ``read(stream, **kwargs)`` and ``write(stream)``,
                such as :class:`~wiithon.formats.bcsv.BCSV` or :class:`~wiithon.formats.rarc.Rarc`
            **kwargs: Forwarded to ``cls.read()``

        Yields:
            The parsed object, ready to modify

        Warning:
            Each call re-reads from the **source** disc. Editing two files inside the same archive with two successive
            calls loses the first edit, because the second call reopens the original archive
            Do both edits in a single block, opening the archive itself as :class:`~wiithon.formats.rarc.Rarc`

        Note:
            If the block raises, nothing is written back

        Example:
            >>> with patcher.edit_as("AstroDome/AstroDome.arc/stageinfo/layera", BCSV, str_fmt="shift_jis") as bcsv:
            ...     for entry in bcsv.entries:
            ...         entry["Timer"] = 0
        """
        data = resolve_read(self, path)
        obj = cls.read(BytesIO(data), **kwargs)
        yield obj
        buf = BytesIO()
        obj.write(buf)
        resolve_write(self, path, buf.getvalue())

    # noinspection PyTypeHints
    def patch_dol(self, fn: Callable[Concatenate[DOL, P], None], *args: P.args, **kwargs: P.kwargs) -> None:
        """
        Register a callback that patches the main executable

        The callback runs during :meth:`build`, on the DOL of the DATA partition

        Args:
            fn: Called with the parsed :class:`~wiithon.formats.dol.DOL`. Modify it in place

        Note:
            Only one callback is kept. Calling this twice replaces the first

        See Also:
            :doc:`/user_guide/patching` for code injection above the arena
        """
        self.dol_modifiers.append(lambda dol: fn(dol, *args, **kwargs))

    def read_dol(self) -> DOL:
        """
        Read the main executable of the source disc

        Returns:
            The parsed DOL, without any pending patch applied
        """
        return self.data_partition.read_dol()

    def get_infos(self) -> dict:
        """
        Summarise the source disc

        Returns:
            A dict with keys ``game_id``, ``title``, ``disc_number`` and ``version``
            ``game_id`` is decoded to ``str`` and stripped of padding
        """
        header = self.reader.disc_header
        return {
            "game_id"    : header.game_id.decode("ascii").strip("\x00"),
            "title"      : header.game_title,
            "disc_number": header.disc_num,
            "version"    : header.disc_version
        }

    def modify_banner_title(self, new_title: str, language: str = "English") -> None:
        """
        Change the title shown in the Wii menu, for one language

        Reads ``opening.bnr``, rewrites its IMET header and queues the result as a replacement

        Args:
            new_title: New title
            language: One of ``Japanese``, ``English``, ``German``, ``French``, ``Spanish``, ``Italian``, ``Dutch``,
                ``Simplified Chinese``, ``Traditional Chinese`` or ``Korean``

        Raises:
            ValueError: If ``language`` is not one of the values above
        """
        bnr_bytes = self.read_file("opening.bnr")
        bnr = BNR.read(BytesIO(bnr_bytes))
        bnr.imet.set_title(new_title, language)
        self.replace_file("opening.bnr", bnr.get_bytes())

    def modify_title(self, new_title: str) -> None:
        """
        Change the game title stored in the disc header

        Args:
            new_title: New title. It is truncated to the field size when written

        Note:
            This changes the disc header only. The name shown in the Wii menu comes from the banner,
            see :meth:`modify_banner_title`
        """
        self.reader.disc_header.game_title = new_title

    def modify_title_id(self, new_id: str) -> None:
        """
        Change the game ID of the disc and of the ticket

        Args:
            new_id: Exactly 6 ASCII characters, such as ``"FEUR69"``

        Raises:
            RuntimeError: If ``new_id`` is not 6 bytes once encoded
            UnicodeEncodeError: If ``new_id`` contains non-ASCII characters

        Note:
            The ticket title ID is rebuilt as ``0x00010000`` followed by the first four characters of the new ID
        """
        b = new_id.encode("ascii")
        if len(b) != 0x06:
            raise RuntimeError(f"Title ID needs to be 6 bytes length, got: {len(b)} with {b}")

        self.reader.disc_header.game_id = b
        self.data_partition.header.ticket.title_id = b'\x00\x01\x00\x00' + b[:4]

    def build(self, output_path: str, progress_cb: Callable | None = None) -> None:
        """
        Write the patched ISO

        Every partition of the source disc is copied to the output
        The DATA partition additionally receives the queued file changes, the FST callback and the DOL callback
        Hashes and encryption are recomputed as required

        Args:
            output_path: Path of the ISO to create. It is overwritten if it exists
            progress_cb: Called with an integer percentage from 0 to 100. It is invoked once per partition,
                so the value restarts at 0 for each

        Note:
            This is where all the work happens. Expect it to take a while and to need free disc space of roughly
            the size of the source ISO
        """
        flush_archive_cache(self)
        builder = WiiDiscBuilder(self.reader.disc_header, self.reader.region)

        output_path = Path(output_path)
        with output_path.open("w+b") as dest:
            for entry in self.reader.partitions:
                is_data = entry.part_type == WiiPartType.DATA
                copy_builder = CopyPartitionSource(
                    self.reader,
                    entry,
                    fst_modifier=self._build_fst_modifier() if is_data else None,
                    dol_modifiers=self.dol_modifiers if is_data else None,
                    file_overrides=self.file_replacements if is_data else None,
                )
                builder.add_partition(dest, copy_builder, progress_cb)

            builder.finish(dest)

    def _build_fst_modifier(self) -> Callable[[FST], None] | None:
        user_modification = self.fst_modifier
        files_to_add = dict(self.files_to_add)
        files_to_remove = list(self.files_to_remove)

        if not user_modification and not files_to_add and not files_to_remove:
            return None

        def modifier(fst: FST) -> None:
            if user_modification:
                user_modification(fst)
            for path, data in files_to_add.items():
                parts = path.split("/")
                node = FSTFile(name=parts[-1], offset=0, length=len(data))
                add_node(fst.entries, parts[:-1], node)
            for path in files_to_remove:
                remove_node(fst.entries, path.split("/"))

        return modifier