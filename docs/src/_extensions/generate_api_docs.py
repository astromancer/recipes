
from pathlib import Path
from collections import defaultdict

from sphinx.application import Sphinx
from sphinx.util.typing import ExtensionMetadata

from recipes.io.walk import iter_package_files


module_template = """
{}
.. automodule:: {}
    :members:
    :show-inheritance:
    :noindex:
"""
index_template = f"""{module_template}

.. toctree::
    :maxdepth: 3

    {{}}
"""


class APIDocTreeGenerator:

    module_template = module_template
    index_template = index_template
    format = 'rst'

    def __init__(self, package_root, package_name=None,
                 library_path=None, docs_source='docs/src', output_folder='api',
                 ignore_file='.gitignore', ignore_patterns=('**/_*.py'),
                 index_filename='index', filename_prefix=None, nested=0,
                 headers='full'
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
        headers : {'full', 'name_only', True, False}:
            How to format headers in the rst files.
        """
        self.package_root = Path(package_root)
        assert self.package_root.exists()
        self.package_name = package_name or package_root.name

        self.docs_source = self.resolve_path(docs_source)
        self.library_path = self.resolve_path(library_path or f'src/{self.package_name}')
        self.output_root = self.resolve_path(output_folder, 'docs_source')

        ignore_file = self.resolve_path(ignore_file)
        self.ignore_file = ignore_file
        self.ignore_patterns = ignore_patterns

        if filename_prefix is None:
            filename_prefix = self.package_name
        self.filename_prefix = str(filename_prefix)
        self.index_filename = index_filename
        self.nested = int(nested)
        self.headers = str(headers)

    def resolve_path(self, path, relative_to='package_root'):
        if not (path := Path(path)).is_absolute():
            path = getattr(self, relative_to) / path
        return path

    def collect(self):
        modules = defaultdict(lambda: defaultdict(list))
        for file in iter_package_files(self.library_path,
                                       ignore_patterns=self.ignore_patterns,
                                       ignore_file=self.ignore_file):
            #
            subpath = file.relative_to(self.library_path).parent
            module = '.'.join((self.package_name, *subpath.parts))
            data = modules[module]

            # collect submodules
            if self.nested:
                # output_name = f'{self.index_filename
                output_path = subpath / file.stem
            else:
                output_path = self.get_output_filename(f'{module}.{file.stem}')

            data['submodules'].append(output_path)

            # get path for subpackage index file
            if 'index' not in data:
                if self.nested:
                    data['index'] = (subpath / self.index_filename)
                else:
                    data['index'] = self.get_output_filename(module) or self.index_filename

            # collect subpackages
            if subpath.parts:
                parent = module.rsplit('.', 1)[0]
                subpackages = modules[parent]['subpackages']
                if (index := data['index']) not in subpackages:
                    subpackages.append(index)

        return modules

    def get_output_filename(self, module):
        return module.replace(self.package_name,
                              self.filename_prefix, 1).strip('.')

    def write_package(self, modules, title=None, dry_run=False):
        header = title
        for module, spec in modules.items():
            self.write_index(module, spec, header, dry_run)
            header = None

            for sub in spec['submodules']:
                file = self.output_root / f'{sub}.{self.format}'
                self.write_module(file, sub, dry_run=dry_run)

    def write_index(self, module, spec, header=None, dry_run=False):

        submodules = spec['submodules']
        subpackages = spec['subpackages']
        if references := [*submodules, *subpackages]:
            # get file header
            header = self.get_header(module, header)
            content = self.index_template.format(header, module,
                                                 '\n    '.join(references))
            index_file = self.output_root / f'{spec["index"]}.{self.format}'
            if dry_run:
                print('-' * 80, f'Dry run: {module}', index_file,
                      '-' * 80, content,
                      '-' * 80, sep='\n')
            else:
                index_file.write_text(content)

    def write_module(self, file, module, header=None, dry_run=False):

        header = self.get_header(module, header)
        content = self.module_template.format(header, module)

        if dry_run:
            print('-' * 80, f'Dry run: {module}', file,
                  '-' * 80, content,
                  '-' * 80, sep='\n')
        else:
            file.parent.mkdir(exist_ok=True)
            file.write_text(content)

    def get_header(self, module, header):

        if not self.headers:
            return ''

        if header is None:
            if self.headers == 'full':
                header = module
            if self.headers == 'name_only':
                header = module.rsplit('.', 1)[-1]

        # underline
        header = str(header)
        return f'{header}\n{"=" * len(header)}\n'

    def run(self, header='API', dry_run=False):

        modules = self.collect()
        self.write_package(modules, header, dry_run)


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
# @click.option('--header')
def main(
    package_root,
    package_name=None,
    library_path=None,
    docs_source='docs/src',
    output_folder='api',
    ignore_file='.gitignore',
    ignore_patterns=('**/_*.py'),
    index_filename='index',
    filename_prefix=None,
    nested=0,
    dry_run=True,
    headers='full',
    title='API'
):

    gen = APIDocTreeGenerator(
        package_root, package_name,
        library_path, docs_source, output_folder,
        ignore_file, ignore_patterns,
        index_filename, filename_prefix, nested, headers
    )
    gen.run(title, dry_run)


if __name__ == '__main__':
    package = Path(__file__, '../../../..').resolve()
    library = package / 'src' / package.name
    ignore = ['**/_*.py', library / 'decorators/examples']
    # docs_src = Path(__file__).parent
    # api_docs = docs_src / 'api'
    main(package,
         ignore_patterns=ignore,
         headers='name_only',
         filename_prefix='')
