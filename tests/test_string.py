
# third-party
import pytest

# local
from recipes.testing import ECHO, Expected, mock
from recipes.string import Percentage, justify, pluralize, sub, title


test_pluralize = Expected(pluralize)({

    # ...sis -> ...ses
    'analysis':     'analyses',
    'antithesis':   'antitheses',
    'basis':        'bases',
    'crisis':       'crises',
    'diagnosis':    'diagnoses',
    'ellipsis':     'ellipses',
    'hypothesis':   'hypotheses',
    'oasis':        'oases',
    'parenthesis':  'parentheses',
    'synopsis':     'synopses',
    'thesis':       'theses',

    # ...(ax/ex) -> ...ces
    'apex':         'apices',       # or apexes
    'appendix':     'appendices',   # or appendixes
    'codex':        'codices',
    'index':        'indices',      # or indexes
    'matrix':       'matrices',  # or matrixes
    'vertex':       'vertices',  # or vertexes
    'vortex':       'vortices',

    # ...(s/sh) ->  ...(s/sh)es
    'success':      'successes',
    'radish':       'radishes',

    # ...us -> ...i
    'nucleus':      'nuclei',
    'radius':       'radii',
    'walrus':       'walruses',
    'alumnus':      'alumni',
    'bacillus':     'bacilli',
    'cactus':       'cacti',  # or cactus, cactuses
    'corpus':       'corpora',
    'focus':        'foci',  # or focuses
    'fungus':       'fungi',
    'locus':        'loci',
    'stimulus':     'stimuli',
    'syllabus':     'syllabi',  # or syllabuses
    # exceptions
    'genus':        'genera',  # or genuses
    'opus':         'opera',  # or opuses

    # ...um -> ...a
    'cilium':       'cilia',
    'addendum':     'addenda',      # or addendums
    'bacterium':    'bacteria',
    'curriculum':   'curricula',  # or curriculums
    'datum':        'data',
    'erratum':      'errata',
    'medium':       'media',        # or mediums
    'memorandum':   'memoranda',  # or memorandums
    'ovum':         'ova',
    'phylum':       'phyla',
    'referendum':   'referenda',  # or referendums
    'stratum':      'strata',
    'symposium':    'symposia',  # or symposiums

    # ...(f/fe) -> ...ves
    'dwarf':        'dwarves',  # or dwarfs
    'half':         'halves',
    'hoof':         'hooves',  # or hoofs
    'knife':        'knives',
    'loaf':         'loaves',
    'scarf':        'scarves',  # or scarfs
    'self':         'selves',
    'thief':        'thieves',
    'wharf':        'wharves',  # or wharfs
    'wife':         'wives',
    'wolf':         'wolves',
    # exception:
    'roof':         'roofs',

    # ...a -> ...ae
    'nova':         'novae',
    'alumna':       'alumnae',
    'antenna':      'antennae',     # or antennas
    'formula':      'formulae',
    'larva':        'larvae',
    'minutia':      'minutiae',
    'nebula':       'nebulae',
    'vertebra':     'vertebrae',
    'vita':         'vitae',
    # exceptions:
    'vista':        'vistas',
    

    # ...eau -> eaux
    'beau':         'beaux',
    'bureau':       'bureaux',
    'château':      'châteaux',
    'tableau':      'tableaux',

    # ...to -> ...ti
    'concerto':     'concerti',  # or concertos
    'graffito':     'graffiti',
    'libretto':     'libretti',  # or librettos
    'photo':        'photos',
    'memento':      'mementos',


    'array':        'arrays',
    'agency':       'agencies',


    'nerd':         'nerds',


    'axis':         'axes',
    'child':        'children',
    'criterion':    'criteria',


    # irregular
    'foot':         'feet',
    'goose':        'geese',
    'tooth':        'teeth',
    # exceptions
    'root':         'roots',


    'man':          'men',
    'woman':        'women',


    'louse':        'lice',
    'mouse':        'mice',


    'die':          'dice',  # or dies
    'ox':           'oxen',
    'phenomenon':   'phenomena',
    'quiz':         'quizzes',
    'fez':          'fezzes',  # or fezes


    # unchanging / context dependent
    'aircraft':     'aircraft',
    'bison':        'bison',
    'deer':         'deer',
    'fish':         'fish',     # or fishes when refering to species of fishes
    'faux pas':     'faux pas',
    'moose':        'moose',
    'offspring':    'offspring',
    'grouse':       'grouse',
    'salmon':       'salmon',
    'series':       'series',
    'sheep':        'sheep',
    'shrimp':       'shrimp',
    'species':      'species',
    'swine':        'swine',
    'trout':        'trout',
    'tuna':         'tuna'
})

test_sub = Expected(sub)({
    # basic
    mock.sub('hello world', {'h':       'm', 'o ':          'ow '}):
        'mellow world',
    mock.sub('hello world', dict(h='m', o='ow', rld='')):
        'mellow wow',
    mock.sub('hello world', {'h':       'm', 'o ':          'ow ', 'l':        ''}):
        'meow word',
    mock.sub('hello world', dict(hell='lo', wo='', r='ro', d='l')):
        'loo roll',
    # character permutations
    mock.sub('option(A, B)', {'B':      'A', 'A':       'B'}):
        'option(B, A)',
    mock.sub('AABBCC', {'A':        'B', 'B':       'C', 'C':          'c'}):
        'BBCCcc',
    mock.sub('hello world', dict(h='m', o='ow', rld='', w='v')):
        'mellow vow',

    mock.sub('dark-SHOC2-8x8-1MHz 2.5 EM: 30', {' ':        '-', "'": '', ':        ':         ''}):
        'dark-SHOC2-8x8-1MHz-2.5-EM30',

    mock.sub(R"""\
     \begin{equation}[Binary vector potential]
        \label{eq:bin_pot_vec}
        Ψ\qty(\vb{r}) = - \frac{GM_1}{\abs{\vb{r - r_1}}}
        \end{equation}""",
             {'_p':     'ₚ', 'eq:bin_pot_vec':      'eq:bin_pot_vec'}):
        ECHO
})


test_title = Expected(title)({
    mock.title('hello world'):                         'Hello World',
    mock.title('hello world', 'world'):                'Hello world',
    mock.title('hello\nworld', 'world'):               'Hello world',
    mock.title('internal in inside', 'in'):            'Internal in Inside',
    mock.title('internal in inside in', 'in'):         'Internal in Inside in',
    mock.title('words for the win', ('for', 'the')):   'Words for the Win',
    mock.title('words for the winter', ('win')):       'Words For The Winter'
})


# _unbracket('{{{hello world!}}}', '{}', condition=lambda x: '!' not in x)
# Out[53]: '{{{hello world!}}}'

# _unbracket('{{{hello world? {this my jam!}}}', '{}', condition=lambda x: '!' not in x)
# Out[54]: '{{{hello world? {this my jam!}}}'


# tests = ['root/{ch{{1,2},{4..6}},main{1,2},{1,2}test}*.png',
#      ...:          'ch{{1,2},{4..6}},main{1,2},{1,2}test']
#      ...: lists(map(bash.splitter, tests))

# [['root/{ch{{1,2},{4..6}},main{1,2},{1,2}test}*.png'],
#  ['ch{{1,2},{4..6}}', 'main{1,2}', '{1,2}test']]


@pytest.mark.parametrize(
    's, e',
    [('20%', 2469),
     ('100.01%', 12346.2345),
     ('12.0001 %', 1481.412345)]
)
def test_percentage(s, e):
    assert Percentage(s).of(12345.) == e


test_justify = Expected(justify)({
    # (justify := mock.justify),
    mock.justify('!\n!', '<', 10): '!         \n!         ',
    mock.justify('!\n!', '>', 10): '         !\n         !',
    mock.justify('!\n!', '>', 10): '    !     \n    !     '
})


# @pytest.mark.parametrize('s', ['3r',
#                                'some text 100.0.ss',
#                                '12.0001 %'])
# def test_percentage_raises(s):
#     n = Percentage(s).of(12345.)
#     print(n)


# def test_hstack(strings):
