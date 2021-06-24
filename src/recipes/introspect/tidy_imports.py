#! /usr/bin/python3

if __name__ == '__main__':
    import sys
    from recipes.introspect.imports import tidy
    import motley

    # TODO: argparse options 

    filename = sys.argv[1]
    debug = False
    print('Tidying import statements in %s' % motley.blue(filename))
    s = tidy(filename, dry_run=debug, report=debug)
