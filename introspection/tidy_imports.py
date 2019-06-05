#! /usr/bin/python3

if __name__ == '__main__':
    import sys
    from recipes.introspection.imports import tidy, print_imports_tree
    import motley

    filename = sys.argv[1]

    print('Tidying import statements in %s' % motley.blue(filename))

    try:
        s = tidy(filename, dry_run=True)

        print_imports_tree(s)

        # if s == '':
        #     print(filename, 'has no imports')

        # print('\n'.join(s.split('\n', 40)[:40]))
        # print('Done.')

    except Exception as err:
        from IPython import embed
        import traceback, textwrap

        header = textwrap.dedent(
                """\
                Caught the following %s:
                ------ Traceback ------
                %s
                -----------------------
                
                """) % (err.__class__.__name__, traceback.format_exc())

        print(header)
        raise
