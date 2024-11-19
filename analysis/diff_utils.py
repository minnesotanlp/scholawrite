import diff_match_patch as dmp_module

dmp = dmp_module.diff_match_patch()

print(dmp.DIFF_INSERT, dmp.DIFF_EQUAL, dmp.DIFF_DELETE)

def count_op(op, revision):
    count = 0
    
    for l in revision:
        curr_op = l[0]

        if (op is None):
            count += len(l[1])
        if curr_op == op:
            count += op * len(l[1])

    return count

def smart_append(arr, character):
  if (len(character) > 0 and character[0].isalpha()):
     arr.append(character)

def get_word_diff(diff_arr):
  dmp.diff_cleanupSemantic(diff_arr)

  before_text = []
  after_text = []

  for diff in diff_arr:
    op, data = diff[0], diff[1]  # Unpack only the operation and text (ignore position)

    DIFF_DELETE = -1
    DIFF_NO_CHANGE = 0
    DIFF_INSERT = 1

    if op == DIFF_DELETE:
        #smart_append(before_text, data)
        before_text.append(data)
    elif op == DIFF_INSERT:
        #smart_append(after_text, data)
        after_text.append(data)
    elif op == DIFF_NO_CHANGE:
        #smart_append(before_text, data)
        #smart_append(after_text, data)
        before_text.append(data)
        after_text.append(data)

  before_result = ''.join(before_text)
  after_result = ''.join(after_text)

  #print("\n\n*******************")
  #print("before word count: ", len(before_result.split()))
  #print("after word count: ", len(after_result.split()))
  #print("before_words: ", before_result.split())
  #print("after_words: ", after_result.split())
  #print("*******************")

  return len(after_result.split()) - len(before_result.split())