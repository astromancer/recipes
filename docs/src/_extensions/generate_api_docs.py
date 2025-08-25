from pathlib import Path

from sphinx.application import Sphinx
from sphinx.util.typing import ExtensionMetadata

from recipes.io import gitignore


module_template = """
{0:}
{1:}

.. automodule:: {2}
    :members:
    :show-inheritance:
    :noindex:
"""
index_template = f"""{module_template}

.. toctree::
    :maxdepth: 3

    {{3}}
"""


class APIDocTreeGenerator:

    module_template = module_template
    index_template = index_template
    format = 'rst'

    def __init__(self, package_root, package_name=None,
                 library_path=None, docs_source='docs/src', output_folder='api',
                 ignore_file='.gitignore', ignore_patterns=('**/_*.py'),
                 index_filename='index', filename_prefix=None, nested=0,
                 ):
        """
        Initializes the APIDocTreeGen instance with configuration for API
        documentation generation.

        Sets up paths, package information, ignore patterns, and output settings
        for generating API documentation.

        Parameters
        ----------
        package_root : str or Path
            The root directory of the package.
        package_name : str, optional
            Name of the package. If not provided, uses the name of
            ``package_root`` folder.
        library_path : str or Path, optional
            Path to the library source code. If not absolute, path should be
            relative to the ``package_root`` folder.
        docs_source : str or Path, optional
            Path to the documentation source folder. If not absolute, path
            should be relative to the ``package_root`` folder.
        output_folder : str or Path, optional
            Folder to output generated API docs. If not absolute, path should be
            relative to the ``docs_source`` folder.
        ignore_file : str or Path, optional
            File with list of ignore patterns.
        ignore_patterns : tuple, optional
            Explicit filenames or file glob patterns to ignore.
        index_filename : str, optional
            Filename for the index file for each (sub)package. Only used if nested != 0
        filename_prefix : str, optional
            Prefix for generated filenames. Use the ``package_name`` by default.
            If an empty string is given, the ``package_name`` will not be
            prefixed to the generated filenames.
        nested : int, optional
            Controls nesting of output folders.

            - If 0, a flat documentation structure will be generaed. Generated
              files are named according to the fully qualified name of module
              they represent eg: ``foo.bar.xyz.rst``
            - If an integer, eg. 1, this determined the maximum depth nested
              directories in the tree.
            - If -1 (the default) a folder tree with structure mirroring that of
              the package will be generated.

        """
        self.package_root = Path(package_root)
        assert self.package_root.exists()
        self.package_name = package_name or package_root.name

        self.docs_source = self.resolve_path(docs_source)
        self.library_path = self.resolve_path(library_path or f'src/{self.package_name}')
        self.output_root = self.resolve_path(output_folder, 'docs_source')

        ignore_file = self.resolve_path(ignore_file)
        self.ignore = gitignore.load(ignore_file, ignore_patterns)

        if filename_prefix is None:
            filename_prefix = self.package_name
        self.filename_prefix = str(filename_prefix)
        self.index_filename = index_filename
        self.nested = int(nested)

    def resolve_path(self, path, relative_to='package_root'):
        if not (path := Path(path)).is_absolute():
            path = getattr(self, relative_to) / path
        return path

    def create_module(self, module, module_path, output_folder,
                      dry_run=False, level=0):
        # print(module, '-' * len(module), sep='\n')
        for sub in module_path.glob('*.py'):
            if self.ignore.match(sub):
                continue

            if self.nested:
                stem = sub.stem
            else:
                base = module.replace(self.package_name, self.filename_prefix, 1)
                stem = f'{base}.{sub.stem}'.lstrip('.')

            yield stem

            file = output_folder / f'{stem}.{self.format}'
            content = self.module_template.format(
                sub.stem, '-' * len(sub.stem), f'{module}.{sub.stem}'
            )

            if dry_run:
                print('-' * 80, f'Dry run: {module}', file,
                      '-' * 80, content,
                      '-' * 80, sep='\n')
            else:
                file.parent.mkdir(exist_ok=True)
                file.write_text(content)

    def create_package(self, path, output_path, module, dry_run=False,
                       title=None, level=0):

        # submodules: Find *.py files and generate those submodule docs first
        submodules = list(
            self.create_module(module, path, output_path, dry_run, level)
        )
        # subpackages: loop through directories
        for sub in path.iterdir():
            if not sub.is_dir() or self.ignore.match(sub):
                continue

            if self.nested:
                sub_path = output_path / sub.name
                reference = f'{sub.name}/{self.index_filename}'
            else:
                sub_path = output_path
                reference = f'{module}.{sub.name}'

            sub_name = f'{module}.{sub.name}'
            self.create_package(
                sub, sub_path, sub_name, dry_run, level=level + 1
            )
            submodules.append(reference)

        if submodules:
            if self.nested:
                file = (output_path / f'{self.index_filename}.{self.format}')
            else:
                base = module.replace(self.package_name, self.filename_prefix, 1).strip('.')
                file = (self.output_root / f'{base}.{self.format}')

            title = title or path.name
            content = self.index_template.format(title,
                                                 '=' * len(title),
                                                 module,
                                                 '\n    '.join(submodules))
            if dry_run:
                print('-' * 80, f'Dry run: {module}', file,
                      '-' * 80, content,
                      '-' * 80, sep='\n')
            else:
                file.write_text(content)

    def run(self, dry_run=False, title='API'):

        self.create_package(
            self.library_path, self.output_root, self.package_name,
            dry_run=dry_run, title=title
        )

# @click.argument('package_root', type=Path)


def setup(app: Sphinx) -> ExtensionMetadata:
    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


# @click.command()
# @click.argument('package_root', nargs=1)
# @click.option('-n', '--package-name')
# @click.option('-l', '--library-path')
# @click.option('-d', '--docs-source')
# @click.option('-o', '--output-folder')
# @click.option('--ignore-file')
# @click.option('--ignore-patterns')
# @click.option('--index-filename')
# @click.option('--filename-prefix')
# @click.option('--nested')
# @click.option('--dry-run')
# @click.option('--title')
def main(package_root, package_name=None,
         library_path=None, docs_source='docs/src', output_folder='api',
         ignore_file='.gitignore', ignore_patterns=('**/_*.py'),
         index_filename='index', filename_prefix=None, nested=0,
         dry_run=False, title=None):

    gen = APIDocTreeGenerator(package_root, package_name,
                              library_path, docs_source, output_folder,
                              ignore_file, ignore_patterns,
                              index_filename, filename_prefix, nested)

    gen.run(dry_run, title)



if __name__ == '__main__':
    package = Path(__file__, '../../../..').resolve()
    library = package / 'src' / package.name
    ignore = ['**/_*.py', library / 'decorators/examples']
    # docs_src = Path(__file__).parent
    # api_docs = docs_src / 'api'
    main(package, ignore_patterns=ignore, dry_run=True)
