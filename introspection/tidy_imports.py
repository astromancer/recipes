#! /usr/bin/python3

if __name__ == '__main__':
    import sys
    from recipes.introspection.imports import tidy

    filename = sys.argv[1]

    print('Tidying import statements in %r' % filename)

    try:
        s = tidy(filename, dry_run=True)
        print('\n'.join(s.split('\n', 40)[:40]))
        print()
        print('Done.')
        print()

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
