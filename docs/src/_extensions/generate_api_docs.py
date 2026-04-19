
import click
import shutil
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
                 library_path=None, docs_source='docs/src', output_folder=None,
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
            Folder to output generated API docs. If None, the default, an output
            folder with the same name as the package will be created in the 
            `docs_source` folder. If not absolute, path should be
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
        self.package_root = Path(package_root).resolve()

        assert self.package_root.exists()
        self.package_name = package_name or self.package_root.name

        self.docs_source = self.resolve_path(docs_source)
        self.library_path = self.resolve_path(library_path or f'src/{self.package_name}')
        self.output_root = self.resolve_path(output_folder or self.package_name, 'docs_source')

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
            self.collect_file(file, modules)

        return dict(zip(modules.keys(), map(dict, modules.values())))

    def collect_file(self, file, modules):
        subpath = file.relative_to(self.library_path).parent
        module = '.'.join((self.package_name, *subpath.parts))
        submodule = f'{module}.{file.stem}'
        module_data = modules[module]

        # collect submodules
        if self.nested:
            # output_name = f'{self.index_filename
            output_path = str(subpath / file.stem)
            reference = file.stem
        else:
            output_path = reference = self.get_output_filename(submodule)

        module_data['submodule_names'].append(submodule)
        module_data['submodule_paths'].append(output_path)
        module_data['toc'].append(reference)

        # get path for subpackage index file
        if 'index_path' not in module_data:
            if self.nested:
                index_file = str(subpath / self.index_filename)
                index_reference = f'{subpath.name}/{self.index_filename}'
            else:
                index_file = index_reference = (
                    self.get_output_filename(module) or self.index_filename)
            module_data['index_path'] = index_file

        # collect subpackages
        if subpath.parts:
            parent = module.rsplit('.', 1)[0]
            subpackages = modules[parent]['subpackage_paths']
            if (index_file := module_data['index_path']) not in subpackages:
                subpackages.append(index_file)
                modules[parent]['toc'].append(index_reference)

    def get_output_filename(self, module):
        return module.replace(self.package_name,
                              self.filename_prefix, 1).strip('.')

    def write_package(self, modules, title=None, dry_run=False):
        for module, spec in modules.items():
            self.write_index(module, spec, title, None, dry_run)

            for name, path, in zip(spec['submodule_names'], spec['submodule_paths']):
                file = self.output_root / f'{path}.{self.format}'
                self.write_module(file, name, dry_run=dry_run)

    def write_index(self, module, spec, title=None, header=None, dry_run=False):

        if references := spec['toc']:
            # get file header
            if title:
                title = self.get_header(title, module, '=')
                header = self.get_header(header, module, '-')
                header = f'{title}\n\n{header}'
                title = None # Only toplevel
            else:
                header = self.get_header(header, module)
            
            content = self.index_template.format(header, module,
                                                 '\n    '.join(references))
            index_file = self.output_root / f'{spec["index_path"]}.{self.format}'
            self._write(index_file, content, dry_run, module)

    def _write(self, path, content, dry_run, module):
        if dry_run:
            print('-' * 80, f'Dry run: {module}', path,
                  '-' * 80, content,
                  '-' * 80, sep='\n')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

    def write_module(self, path, module, header=None, dry_run=False):

        header = self.get_header(header, module, '-')
        content = self.module_template.format(header, module)
        self._write(path, content, dry_run, module)

    def get_header(self, header, module, level='='):

        if not self.headers:
            return ''

        if header is None:
            if self.headers == 'full':
                header = module
            if self.headers == 'name_only':
                header = module.rsplit('.', 1)[-1]

        # underline
        header = str(header)
        return f'{header}\n{level * len(header)}\n'

    def run(self, title='API', dry_run=False):

        modules = self.collect()
        self.write_package(modules, title, dry_run)

    def clean(self):
        if self.output_root.exists():
            shutil.rmtree(self.output_root)


def setup(app: Sphinx) -> ExtensionMetadata:
    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


def main(package_root,
         package_name=None,
         library_path=None,
         docs_source='docs/src',
         output_folder='api',
         ignore_file='.gitignore',
         ignore_patterns=('**/_*.py'),
         index_filename='index',
         filename_prefix=None,
         nested=0,
         dry_run=False,
         headers='full',
         title='API'):

    print('Generating API docs.')
    gen = APIDocTreeGenerator(
        package_root, package_name,
        library_path, docs_source, output_folder,
        ignore_file, ignore_patterns,
        index_filename, filename_prefix, nested, headers
    )
    # remove any pre-existing output
    gen.clean()
    # Generate the docs
    gen.run(title, dry_run)


@click.command()
@click.argument('package_root', default='.', type=click.Path())
@click.option('-n', '--package-name', default=None)
@click.option('-l', '--library-path', default=None,)
@click.option('-d', '--docs-source', default='docs/src',)
@click.option('-o', '--output-folder', default='api',)
@click.option('--ignore-file', default='.gitignore',)
@click.option('--ignore-patterns', default=('**/_*.py'),)
@click.option('--index-filename', default='index',)
@click.option('--filename-prefix', default=None,)
@click.option('--nested', default=False, is_flag=True)
@click.option('--dry-run', default=False, is_flag=True)
@click.option('--headers', default='full', )
@click.option('--title', default='API')
def cli_runner(package_root, package_name,
               library_path, docs_source,
               output_folder,
               ignore_file, ignore_patterns,
               index_filename, filename_prefix,
               nested, dry_run,
               headers, title):

    main(package_root, package_name,
         library_path, docs_source,
         output_folder,
         ignore_file, ignore_patterns,
         index_filename, filename_prefix,
         nested, dry_run,
         headers, title)


if __name__ == '__main__':
    cli_runner()
