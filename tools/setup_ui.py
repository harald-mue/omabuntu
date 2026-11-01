"""Original Omabuntu terminal presentation; no upstream art/assets required."""
import os
import shutil
import sys
import textwrap

GLYPHS = {
    'O': (' ### ', '#   #', '#   #', '#   #', ' ### '),
    'M': ('#   #', '## ##', '# # #', '#   #', '#   #'),
    'A': (' ### ', '#   #', '#####', '#   #', '#   #'),
    'B': ('#### ', '#   #', '#### ', '#   #', '#### '),
    'U': ('#   #', '#   #', '#   #', '#   #', ' ### '),
    'N': ('#   #', '##  #', '# # #', '#  ##', '#   #'),
    'T': ('#####', '  #  ', '  #  ', '  #  ', '  #  '),
}


BLOCK_WORDMARK = (
    '   █▀█ █▀▄▀█ ▄▀█ █▄▄ █░█ █▄░█ ▀█▀ █░█',
    '   █▄█ █░▀░█ █▀█ █▄█ █▄█ █░▀█ ░█░ █▄█',
)


def wordmark(ascii_only=False):
    if not ascii_only:
        return '\n'.join(BLOCK_WORDMARK)
    return '\n'.join('  ' + '  '.join(GLYPHS[letter][row] for letter in 'OMABUNTU')
                     for row in range(5))


def confirm(message):
    """Keep a separate approval gate, with Enter accepting its displayed default."""
    try:
        answer = input(message.rstrip() + ' [Y/n] ').strip().lower()
    except EOFError:
        return False  # Missing terminal input is never an affirmative answer.
    return answer in ('', 'y', 'yes')


class Console:
    def __init__(self, stream=None, plain=False, environ=None, width=None):
        self.stream = sys.stdout if stream is None else stream
        env = os.environ if environ is None else environ
        self.color = (not plain and 'NO_COLOR' not in env and env.get('TERM') != 'dumb'
                      and self.stream.isatty())
        self.width = width or shutil.get_terminal_size((80, 24)).columns
        self.unicode = env.get('TERM') != 'dumb'
        try:
            wordmark().encode(getattr(self.stream, 'encoding', None) or 'utf-8')
        except (UnicodeEncodeError, LookupError):
            self.unicode = False

    def paint(self, text, code):
        return '\033[' + code + 'm' + text + '\033[0m' if self.color else text

    def line(self, text=''):
        print(text, file=self.stream)

    def welcome(self, mode):
        self.line()
        art = wordmark(ascii_only=not self.unicode)
        if max(map(len, art.splitlines())) > self.width:
            art = '  OMABUNTU'
        self.line(self.paint(art, '1;38;5;208'))
        self.line()
        tagline_indent = '          ' if self.width >= 40 else '  '
        self.line(self.paint(tagline_indent + 'Your Ubuntu. Reimagined.', '90'))
        self.line(self.paint('  ' + mode + '  /  Ubuntu 26.04', '1'))
        self.line(self.paint('  ' + '-' * min(60, max(10, self.width - 4)), '90'))

    def step(self, index, title, status, detail):
        color = {'OK': '32', 'CHECK': '33', 'PLANNED': '36', 'BLOCKED': '31'}[status]
        self.line('  ' + self.paint('[%s]' % status, color) + '  %02d  %s' % (index, title))
        for line in detail.splitlines():
            for wrapped in textwrap.wrap(line, width=max(18, self.width - 14)) or ['']:
                self.line('            ' + wrapped)
        self.line()
