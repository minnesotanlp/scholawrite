import diff_match_patch as dmp_module
import re

def diff_linesToWords(text1, text2):
    """Split two texts into an array of strings.  Reduce the texts to a string
    of hashes where each Unicode character represents one line.

    Args:
      text1: First string.
      text2: Second string.

    Returns:
      Three element tuple, containing the encoded text1, the encoded text2 and
      the array of unique strings.  The zeroth element of the array of unique
      strings is intentionally blank.
    """
    lineArray = []  # e.g. lineArray[4] == "Hello\n"
    lineHash = {}   # e.g. lineHash["Hello\n"] == 4

    # "\x00" is a valid character, but various debuggers don't like it.
    # So we'll insert a junk entry to avoid generating a null character.
    lineArray.append('')

    def diff_linesToCharsMunge(text):
      """Split a text into an array of strings.  Reduce the texts to a string
      of hashes where each Unicode character represents one line.
      Modifies linearray and linehash through being a closure.

      Args:
        text: String to encode.

      Returns:
        Encoded string.
      """
      chars = []
      # Walk the text, pulling out a substring for each line.
      # text.split('\n') would would temporarily double our memory footprint.
      # Modifying text would create many large strings to garbage collect.
      lineStart = 0
      lineEnd = -1
      while lineEnd < len(text) - 1:
        
        # Linghe's modification begin
        lineEnd = re.search(r'[\n ]', text[lineStart:])
        if lineEnd:
            lineEnd = lineStart + lineEnd.start()
        else:
            lineEnd = -1
        # linghe's modification ends

        if lineEnd == -1:
          lineEnd = len(text) - 1
        line = text[lineStart:lineEnd + 1]

        if line in lineHash:
          chars.append(chr(lineHash[line]))
        else:
          if len(lineArray) == maxLines:
            # Bail out at 1114111 because chr(1114112) throws.
            line = text[lineStart:]
            lineEnd = len(text)
          lineArray.append(line)
          lineHash[line] = len(lineArray) - 1
          chars.append(chr(len(lineArray) - 1))
        lineStart = lineEnd + 1
      return "".join(chars)

    # Allocate 2/3rds of the space for text1, the rest for text2.
    maxLines = 666666
    chars1 = diff_linesToCharsMunge(text1)
    maxLines = 1114111
    chars2 = diff_linesToCharsMunge(text2)
    return (chars1, chars2, lineArray)


# modifed to python version based on https://github.com/google/diff-match-patch/wiki/Line-or-Word-Diffs#word-mode
def diff_wordMode(text1, text2):
  dmp = dmp_module.diff_match_patch()
  a = diff_linesToWords(text1, text2)
  lineText1 = a[0]
  lineText2 = a[1]
  lineArray = a[2]
  diffs = dmp.diff_main(lineText1, lineText2, False)
  dmp.diff_charsToLines(diffs, lineArray)
  dmp.diff_cleanupSemantic(diffs)
  return diffs

def diff_for_llm(before_text, after_text):
  word_level_diff = diff_wordMode(before_text, after_text)
  output_text = ""
  for each in word_level_diff:
    if each[0] == 0:
      output_text += f"<same>{each[1]}</same>"
    elif each[0] == 1:
      output_text += f"<add>{each[1]}</add>"
    elif each[0] == -1:
      output_text += f"<del>{each[1]}</del>"
  return output_text
