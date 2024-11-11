from readability import Readability

import pydetex.pipelines as pip
from pylatexenc.latexwalker import LatexWalker, LatexMacroNode, LatexCharsNode
from pylatexenc.latex2text import LatexNodes2Text

import re

latex=""
with open("./iter_generation_99.txt") as file:
    latex = file.read()

walker_obj = LatexWalker(latex)
(nodelist, pos, len_) = walker_obj.get_latex_nodes(pos=0)

for each in nodelist:
    if each.isNodeType(LatexMacroNode) and each.macroname == "title":
        title = LatexNodes2Text().node_arg_to_text(each, 0)
        title =re.sub(r'\n{2,}', '\n', title)

new_text = pip.strict(latex)

new_text ='\n\n'.join([title, new_text])

print(new_text)

# raw latex
r = Readability(latex)
f = r.flesch()
print(f.score)
print(f.ease)
print(f.grade_levels)
print("-"*100)

# latex to text with a lot spaces and line break
r = Readability(LatexNodes2Text().latex_to_text(latex))
f = r.flesch()
print(f.score)
print(f.ease)
print(f.grade_levels)
print("-"*100)

# latex to text with less space and line break.
r = Readability(new_text)
f = r.flesch()
print(f.score)
print(f.ease)
print(f.grade_levels)
print("-"*100)
