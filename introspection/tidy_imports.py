#! /usr/bin/python3

if __name__ == '__main__':
    import sys
    from recipes.introspection.imports import tidy

    filename = sys.argv[1]

    print('Tidying import statements in %r' % filename)
    s = tidy(filename, dry_run=True)
    print()
    print(s)
    print()
    print('Done.')
