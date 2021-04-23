
@contextmanager
def backed_up(filename, mode='w', backupfile=None, exception_hook=None):
    """
    Context manager for doing file operations under backup. This will backup
    your file before any read / writes are attempted. If something goes terribly
    wrong during the attempted operation, the original content will be restored.


    Parameters
    ----------
    filename : str or Path
        The file to be edited.
    mode : str, optional
        File mode for opening, by default 'w'.
    backupfile : str or Path, optional
        Location of the backup file, by default None. The default location will
        is the temporary file created by `tempfile.mkstemp`, using the prefix
        "backup." and suffix being the original `filename`.
    exception_hook : callable, optional
        Hook to run on the event of an exception if you wish to modify the
        error message. The default, None, will leave the exception unaltered.

    Examples
    --------
    >>> Path('foo.txt').write_text('Important stuff')
    ... with safe_write('foo.txt') as fp:
    ...     fp.write('Some additional text')
    ...     raise Exception('Catastrophy!')
    ... Path('foo.txt').read_text()
    'Important stuff' # original content was restored. Catastrophy averted!

    Raises
    ------
    Exception
        The type and message of exceptions raised by this context manager are
        determined by the optional `exception_hook` function.
    """
    # write formatted entries
    # backup and restore on error!
    path = Path(filename).resolve()
    backup_needed = path.exists()
    if backup_needed:
        if backupfile is None:
            bid, backupfile = tempfile.mkstemp(prefix='backup.',
                                               suffix=f'.{path.name}')
        else:
            backupfile = Path(backupfile)

        # create the backup
        shutil.copy(str(path), backupfile)

    # write formatted entries
    with path.open(mode) as fp:
        try:
            yield fp
        except Exception as err:
            if backup_needed:
                fp.close()
                os.close(bid)
                shutil.copy(backupfile, filename)
            if exception_hook:
                raise exception_hook(err, filename) from err
            raise
