from pathlib import Path

template = """
{0:}
{1:}

.. automodule:: {2}
    :members:
    :show-inheritance:
    :noindex:
"""
index_template = f"""{template}

.. toctree::
    :maxdepth: 3

    {{3}}
"""


def create_api_docs(path, output_folder, module, ignore, dry_run=False):
    # print(module, '-' * len(module), sep='\n')
    for sub in path.glob('*.py'):
        if sub.name.startswith('_') or sub in ignore:
            continue

        yield sub.stem

        file = output_folder / f'{sub.stem}.rst'
        content = template.format(sub.stem, '-' * len(sub.stem), f'{module}.{sub.stem}')

        if dry_run:
            print(f'Dry run: {module}', file, content, sep='\n')
        else:
            file.parent.mkdir(exist_ok=True)
            file.write_text(content)


def create_api_docs_module(path, output_path, module, ignore=None, dry_run=False, title=None):
    
    ignore = ignore or []
    submodules = list(create_api_docs(path, output_path, module, ignore, dry_run))

    for sub in path.iterdir():
        if sub.is_dir() and not sub.name.startswith('_') and sub not in ignore:
            name = f'{module}.{sub.name}'
            create_api_docs_module(sub, output_path / sub.name, name, ignore, dry_run)
            submodules.append(f"{sub.name}/index")

    if submodules:
        file = (output_path / 'index.rst')
        content = index_template.format(title or path.name,
                                        '=' * len(path.name),
                                        module,
                                        '\n    '.join(submodules))
        if dry_run:
            print(f'Dry run: {module}', file, content, sep='\n')
        else:
            file.write_text(content)

# from recipes.io import iter_files, read_lines

if __name__ == '__main__':
    package_name = 'recipes'
    docs_src = Path(__file__).parent
    api_docs = docs_src / 'api'
    package = Path(docs_src, '..', '..').resolve()
    library = package / 'src' / package_name
    # ignore = package / '.gitignore'
    ignore = [library / 'decorators/examples']
    
    # iter_files(library, '.py', recurse=True, ignore=read_lines(ignore))
    # TODO: (git)ignore
    
    create_api_docs_module(library, api_docs, package_name, ignore, 
                           dry_run=False, title='API')
