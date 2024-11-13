from readability import Readability
import os
import pydetex.pipelines as pip
from pylatexenc.latexwalker import LatexWalker, LatexMacroNode, LatexCharsNode
from pylatexenc.latex2text import LatexNodes2Text

import re


def process_latex(latex):

    walker_obj = LatexWalker(latex)
    (nodelist, pos, len_) = walker_obj.get_latex_nodes(pos=0)

    for each in nodelist:
        if each.isNodeType(LatexMacroNode) and each.macroname == "title":
            title = LatexNodes2Text().node_arg_to_text(each, 0)
            title =re.sub(r'\n{2,}', '\n', title)

    # new_text = pip.strict(latex)
    # new_text ='\n\n'.join([title, new_text])


    new_text = LatexNodes2Text().latex_to_text(latex)


    # raw latex
    # r = Readability(latex)
    # f = r.flesch()
    # print(f.score)
    # print(f.ease)
    # print(f.grade_levels)
    # print("-"*100)

    # # latex to text with a lot spaces and line break
    # r = Readability(LatexNodes2Text().latex_to_text(latex))
    # f = r.flesch()
    # print(f.score)
    # print(f.ease)
    # print(f.grade_levels)
    # print("-"*100)

    # latex to text with less space and line break.
    r = Readability(new_text)
    f = r.flesch()
    print(f.score)
    print(f.ease)
    print(f.grade_levels)
    print("-"*100)


def main():
    abs_path = "/workspace/iterative_writing_eval_2"
    outputs = ["llama3_output", "llama8_output"]
    all_seeds = ["seed1", "seed2", "seed3"]

    for output in outputs:
        for seed in all_seeds:
            path_to_folder = os.path.join(abs_path, output, seed, "generation/iter_generation_99.txt")
            with open(path_to_folder) as file:
                text = file.read()
                print(output, seed)
                process_latex(text)


if __name__ == "__main__":
    main()