
# std
import io

# relative
from .gitignore import GitIgnore
from .mmap import load_memmap, load_memmap_nans
from .utils import (
    backed_up, count_lines, deserialize, guess_format, iter_ext, iter_files,
    iter_lines, load_json, load_pickle, md5sum, open_any, read_line,
    read_lines, safe_write, save_json, save_pickle, serialize, show_tree, walk,
    working_dir, write_lines, write_replace
)


class FileIOPicklable(io.FileIO):
    """
    File object (read-only) that can be pickled.

    This class provides a file-like object (as returned by :func:`open`, namely
    :class:`io.FileIO`) that, unlike standard Python file objects, can be
    pickled. Only read mode is supported.
    When the file is pickled, filename and position of the open file handle in
    the file are saved. On unpickling, the file is opened by filename, and the
    file is seeked to the saved position.
    This means that for a successful unpickle, the original file still has to
    be accessible with its filename.

    Note
    ----
    This class only supports reading files in binary mode. 

    Parameters
    ----------
    name : str
        text or byte string giving the name (and the path if the file isn't in
        the current working directory) of the file to be opened.
    mode : str
        Only reading ('r') mode works. It exists to be consistent with a wider
        API.

    Example
    -------
    ::
        >>> file = FileIOPicklable(PDB)
        >>> file.readline()
        >>> file_pickled = pickle.loads(pickle.dumps(file))
        >>> print(file.tell(), file_pickled.tell())
            55 55
    """

    def __init__(self, name, mode='r'):
        self._mode = mode
        super().__init__(name, mode)

    def __getstate__(self):
        if 'r' not in self._mode:
            raise RuntimeError(f'Can only pickle files that were opened in'
                               f' read mode, not {self._mode}')
        return self.name, self.tell()

    def __setstate__(self, args):
        name = args[0]
        super().__init__(name, mode='r')
        self.seek(args[1])
