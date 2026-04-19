# third-party
import pytest

# local
from recipes.string.regex import RGX_VERBOSE_FLAG, uncomment


@pytest.mark.parametrize(
    'pattern, cleaned',
    [('(?aiLmsux)', '(?aiLmsu)'),
     ('(?axiu)', '(?aiu)'),
        ('(?x)', ''),
        ('(?sm)(stuff!)', '(?sm)(stuff!)')]
)
def test_find_verbose_flag(pattern, cleaned):
    assert RGX_VERBOSE_FLAG.sub(r'\1\2\3', pattern) == cleaned


@pytest.mark.parametrize(
    'pattern, terse',
    {r'''
      [0-9]            # 1 Number
      [A-Z]            # 1 Uppercase Letter
      [a-y]            # 1 lowercase, but not z
      z                # gotta have z...
      ''': 
        r'[0-9][A-Z][a-y]z',
     # python string regex
     r'''(?xsm)                          # verbose, dotall (. matches newline)
      (?P<pre>                            # preceeding content
          ^\s*                            #   whitespace
          [^#'"\n]*?                      #   not comment and not opening quote
      )
      (?P<marks>(?i:(?:[rf]|[rb]){0,2}))  # string class indicator
      (?P<quote>                          # quote characters
          (?P<q>['"]){1}(?:(?P=q){2})?    #   single or triple quote
      )
      (?P<content>.*?)                    # string contents
      (?<!\\)                             # ignore escaped quotes \' \"
      (?P=quote)                          # closing quote
      (?P<post>[^\n]*)                    # any trailing code up to newline
      ''':
      r'(?sm)(?P<pre>^\s*[^)(?P<marks>(?i:(?:[rf]|[rb]){0,2}))'
      r'''(?P<quote>(?P<q>['"]){1}(?:(?P=q){2})?)(?P<content>.*?)(?<!\\)'''
      r'(?P=quote)(?P<post>[^\n]*)',
     # latex comment block
     r'''
      (?xm)
      (^
          (?<!\\)%
          (?P<ws>   [^\n\S]*)
          (?P<text> [^\n]*)
      \n?
      )+
      ''':
      r'(?m)(^(?<!\\)%(?P<ws>[^\n\S]*)(?P<text>[^\n]*)\n?)+'  ,
     # latex citation
     r'''(?xis)
      # name
      # ------------------------------------------------------------------ #
      #([^%\n]|\\%)*?
      (?P<cmd>\\                  # opening \ literal
        # all the various cite-like commands as well as biblatex multicites
        (?P<name>
          defcitealias|
          (?:                     # NOTE: empty group matched here
            |[pf]?no(?:te)?
            |paren
            |(?:foot)?(?:full)?
            |text|smart|super|auto
            |(?:(?:f|t|ft)|[psa]|)vol
          )
          cite(?:s)?
          (?:                     # NOTE: empty group here
            |(?:al)?[tp]
            |(?:t|p|)alias
            |(?:full)?author
            |name|num|date|field|list|title|text|url|year(?:par)?
          )                       # end group: name
          \*?                     # star variant of command?
        ) 
      )                           # end group: cmd
      \s*                         # any trailing whitespace
      # notes
      # ------------------------------------------------------------------ #
      (                           # group: multinotes
        \(\s*                     # possible multicite pre- & post notes
          (?P<multinotes>.*?)\s*  # between ()
        \)\s*
      ){0,2}                      # up to 2 groups: (pre) or (pre)(post) 
      (?P<params>                 # parameters group (optional and required)
        (
          \[\s*
            (?P<prenotes>.*?)\s*  # possible prenote []
          \]
        )?\s*
        (?(prenotes)              # look for postnote [] if prenote exists
          (
            \[\s*
              (?P<postnotes>.*?)\s*
            \]
          )?
        )\s*                      # end of notes
        # required paremeters
        # ---------------------------------------------------------------- #
        (?P<req>
          \{                        # open parameters
            [\s,*]*                 # any leading space or , or literal * (mcite)
            (?P<keys>
              (?:
                (?P<key>[^},\s]+)     # cite key(s)
                (?P<trailspace>\s*)   # bib(la)tex is sensitive to trailing spaces
                ,?\s*                 # comma separated list
              )*                      # possibly multiple keys in one cite call
            )
          \}                        # close parameters
        )
      )+                          # repeat params group for `multicite` command
      ''':
        r'(?is)(?P<cmd>\\(?P<name>defcitealias|'
        r'(?:|[pf]?no(?:te)?|paren|(?:foot)?(?:full)?|text|smart|super|auto|'
        r'(?:(?:f|t|ft)|[psa]|)vol)cite(?:s)?(?:|(?:al)?[tp]|(?:t|p|)alias|'
        r'(?:full)?author|name|num|date|field|list|title|text|url|year(?:par)?)'
        r'\*?))\s*(\(\s*(?P<multinotes>.*?)\s*\)\s*){0,2}'
        r'(?P<params>(\[\s*(?P<prenotes>.*?)\s*\])?\s*(?(prenotes)'
        r'(\[\s*(?P<postnotes>.*?)\s*\])?)\s*(?P<req>\{[\s,*]*'
        r'(?P<keys>(?:(?P<key>[^},\s]+)(?P<trailspace>\s*),?\s*)*)\}))+',
     # latex format string matcher
     r'''(?x)
        # :?
        (?P<spec>
            (?: # non-capture
                (?P<fill>[^{}])      # fill only valid if followed by align
                (?=[<>=^])           # lookahead (doesn't consume)
            )?
            (?P<align>[<>=^]?)       # can have align without fill
            (?P<sign>[+\- ]?)
            (?P<alt>\#?)
            (?P<width>\d*)
            (?P<grouping>[_,]?)
            (?P<precision>(?:\.\d+)?)
            (?P<type>[bcdeEfFgGnosxX%]?)
        )
        # Colour / style format directives
        (?P<style>
            (\|(?P<fg>[ \w,\[\]\(\)_\- ]*))?  # foreground 
            (/ (?P<bg>[ \w,\[\]\(\) ]*))?     # background 
        )
      \}
      ''':
        r'(?P<spec>(?:(?P<fill>[^{}])(?=[<>=^]))?(?P<align>[<>=^]?)'
        r'(?P<sign>[+\-]?)(?P<alt>?)(?P<width>\d*)(?P<grouping>[_,]?)'
        r'(?P<precision>(?:\.\d+)?)(?P<type>[bcdeEfFgGnosxX%]?))'
        r'(?P<style>(\|(?P<fg>[\w,\[\]\(\)_\-]*))?(/(?P<bg>[\w,\[\]\(\)]*))?)\}'
     }.items()
)
def test_uncomment(pattern, terse):
    result = uncomment(pattern)
    assert result == terse
    