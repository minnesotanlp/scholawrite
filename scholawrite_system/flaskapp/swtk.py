import copy
from config import sent_tokenizer, console


def sentence_reform(splits):
    j = 0
    while j < len(splits):
        if j + 1 < len(splits) and (splits[j][-1:] == '\n') and splits[j + 1][0] != '\n':
            splits[j + 1] = splits[j][-1:] + splits[j + 1][:]
            splits[j] = splits[j][:-1]
            j += 1
        elif (splits[j][-1:] == '\n') and in_range(splits, j):
            splits.insert(j + 1, splits[j][-1:])
            splits[j] = splits[j][:-1]
            j += 2
        else:
            j += 1
    k = 0
    while k < len(splits):
        if splits[k] == '':
            splits.pop(k)
        k += 1
    return splits


def exist_and_not_skip(i, text, skip):
    try:
        if (text[i][0]) != skip:
            return True
        else:
            return False
    except IndexError:
        return True


def in_range(text, j):
    if j + 1 == len(text):
        return True
    elif text[j + 1][0] == '\n':
        return True
    return False


def clean_up_info(info, state):
    info.pop('onkey')
    if state == 0 or state == 4:
        info['state'] = info['message']
    elif state == 1:
        try:
            info['clipboard'] = info.pop('cb')
        except:
            console.log(info)
            info['clipboard'] = "No CB Data"

        info['state'] = info['message']
    elif state == 2:
        try:
            info['clipboard'] = info.pop('cb')
        except:
            console.log(info)
            info['clipboard'] = "No CB Data"
            
        info['state'] = info['message']
    elif state == 3:
        try:
            info['clipboard'] = info.pop('cb')
        except:
            console.log(info)
            info['clipboard'] = "No CB Data"

        info['state'] = info['message']
        info["text"] = info["revision"]
        info["revision"] = info.pop("changemade")


def find_front(i, skip, text):
    front = ""
    check = 0
    if (text[i][1].count('\n') == 1) or (text[i][1].count(' ') == 1 and len(text[i][1]) > 1
                                         and exist_and_not_skip(i - 1, text, skip)):
        return check, front
    for k in range(i - 1, -1, -1):
        if text[k][0] == skip:
            check = 1
            k -= 1
        else:
            if (text[k][1].rfind(" ") == (len(text[k][1]) - 1)) or (text[k][1].rfind("\n") == (len(text[k][1]) - 1)):
                return check, front
            elif (text[k][1].rfind(" ") != 0) or (text[k][1].rfind("\n") != 0):
                idx2 = text[k][1].rfind(" ")
                idx3 = text[k][1].rfind("\n")
                if idx3 > idx2:
                    idx2 = idx3
                if idx2 == -1:
                    front = text[k][1] + front
                else:
                    front = text[k][1][idx2 + 1:] + front
                    return check, front
    return check, front


def find_back(i, operation, skip, text):
    back = ""
    check = 0
    if (text[i][1].count('\n') == 1) or (
            text[i][1].count(' ') == 1 and len(text[i][1]) > 1 and exist_and_not_skip(i + 1, text, skip)):
        return check, back
    for k in range(i + 1, len(text)):
        if text[k][0] == skip or len(text[k]) > 2:
            if text[k][0] == skip:
                check = 1
            k += 1
        else:
            idx = -1
            idx1 = text[k][1].find(" ")
            idx2 = text[k][1].find("\n")
            if idx2 >= 0 > idx1:
                idx = idx2
            elif idx1 >= 0 > idx2:
                idx = idx1
            elif idx1 > idx2 >= 0:
                idx = idx2
            elif idx2 > idx1 >= 0:
                idx = idx1
            if text[k][0] != 0:
                text[k].append(1)
                back += text[k][1]
            elif idx == 0:
                if text[k][0] == operation:
                    back += text[k][1]
                return check, back
            else:
                if idx == -1:
                    back += text[k][1]
                else:
                    if text[k][0] == operation:
                        back += text[k][1]
                    else:
                        back += text[k][1][:idx]
                    return check, back
    return check, back


def paste_count_char(text, revision):
    i = 0
    pos = 0
    for j in range(len(text)):
        try:
            if text[j] != revision[j]:
                i = j - 1
                break
            if j == (len(text) - 1):
                i = len(text) - 1
        except IndexError:
            i = j - 1
            break
    if text[i] == '\n' or text[i - 1] == '\n':
        return pos
    for k in range(i, -1, -1):
        if text[k] == '\n':
            break
        pos += 1
    return pos


def count_char(op, i, text):
    pos = 0
    try:
        if "\n" == text[i][1][0]:
            return pos
    except:
        pass
    for k in range(i - 1, -1, -1):
        if op == -1 and (text[k][0] == 1 or text[k][0] == -1):
            k -= 1
        elif text[k][0] == -1 and op == 1:
            k -= 1
        else:
            idx = text[k][1].rfind("\n")
            if idx == (len(text[k][1]) - 1):
                break
            elif idx == -1:
                pos += len(text[k][1])
            else:
                pos += len(text[k][1][idx + 1:])
                break
    return pos


def paste_handler(pre, cur, order):
    # if order is 1, mean cur is longer than pre
    # if order is 2, means pre is longer than cur
    change = ""
    i = 0
    j = 0
    diff_section1 = []
    diff_section2 = []

    # use to handle some edge cases
    # if there is no text in the editor now, means user paste an empty string and overwrite entire text
    # if there is no text in the editor before, means entire text are paste by user
    if not cur:
        print("".join(pre[:]), "--deleted")
        return
    elif not pre:
        print("".join(cur[:]), "--added")
        return

    # const_pre and const_cur is used to reconstruct the original text
    original_pre = copy.deepcopy(pre)
    original_cur = copy.deepcopy(cur)
    for k in range(len(pre)):
        if pre[k][0] == '\n':
            pre[k] = pre[k][1:]
    for k in range(len(cur)):
        if cur[k][0] == '\n':
            cur[k] = cur[k][1:]

    # use to handle most common cases
    switch = 0
    if len(pre) == len(cur):
        length = len(pre)
        for i in range(length):
            if pre[i] != cur[i]:
                diff_section1.append(original_pre[i])
                diff_section2.append(original_cur[i])
    elif order == 1:
        long = cur
        short = pre
        original_long = original_cur
        original_short = original_pre
        length = len(pre)
        while i < length:
            if short[i] != long[i]:
                if switch:
                    diff_section1.append(original_long.pop(i))
                    long.pop(i)
                else:
                    diff_section2.append(original_long.pop(i))
                    long.pop(i)
            elif short[i] == long[i]:
                i += 1
            j += 1
            if len(pre) > len(cur):
                switch = 1
                length = len(cur)
                long = pre
                short = cur
                original_long = original_pre
                original_short = original_cur
            elif switch == 1 and len(cur) > len(pre):
                switch = 0
                length = len(pre)
                long = cur
                short = pre
                original_long = original_cur
                original_short = original_pre
        if i < len(long):
            diff_section1.extend(original_short[i - 1:])
            diff_section2.extend(original_long)
    else:
        long = pre
        short = cur
        original_long = original_pre
        original_short = original_cur
        length = len(cur)
        while i < length:
            if short[i] != long[i]:
                if switch:
                    diff_section2.append(original_long.pop(i))
                    long.pop(i)
                else:
                    diff_section1.append(original_long.pop(i))
                    long.pop(i)
            elif short[i] == long[i]:
                i += 1
            j += 1
            if len(pre) < len(cur):
                switch = 1
                length = len(pre)
                long = cur
                short = pre
                original_long = original_cur
                original_short = original_pre
            elif switch == 1 and len(cur) < len(pre):
                switch = 0
                length = len(cur)
                long = pre
                short = cur
                original_long = original_pre
                original_short = original_cur
        if i < len(long):
            diff_section1.extend(original_long)
            diff_section2.extend(original_short[i - 1:])

    diff_sentence1 = "".join(diff_section1[:1])
    for a in range(1, len(diff_section1[1:]) + 1):
        if diff_section1[a][0] != '\n':
            diff_sentence1 += " " + diff_section1[a]
        else:
            diff_sentence1 += diff_section1[a]

    diff_sentence2 = "".join(diff_section2[:1])
    for b in range(1, len(diff_section2[1:]) + 1):
        if diff_section2[b][0] != '\n':
            diff_sentence2 += " " + diff_section2[b]
        else:
            diff_sentence2 += diff_section2[b]


    if diff_sentence1 == "" and diff_sentence2 == "":
        change = "All lines are the same"
    elif diff_sentence1 == "" and diff_sentence2 != "":
        change = diff_sentence2 + "--added"
    elif diff_sentence1 != "" and diff_sentence2 == "":
        change = diff_sentence1 + "--deleted"
    elif diff_sentence1 != "" and diff_sentence2 != "":
        change = diff_sentence1 + "->" + diff_sentence2

    return change


def tokenize_keystroke(info):
    text = info['revision']
    line_num = info['line']
    length = len(text)
    changes = []
    revise_word = []
    index = 0
    for i in range(length):
        front = ""
        back = ""
        if len(text[i]) > 2 or text[i][0] != -1:
            continue
        elif (text[i][0] == -1) and (0 < i < length - 1):
            check2, front = find_front(i, 1, text)
            check1, back = find_back(i, -1, 1, text)
            pos = count_char(-1, i, text)
            if check1 or check2:
                revise_word.append(
                    '(' + str(line_num) + ',' + str(pos - len(front)) + ')' + ", " + front + text[i][
                        1] + back + "->")
            elif back != "":
                check2, front1 = find_front(i, -1, text)
                check1, back1 = find_back(i, -1, -1, text)
                changes.append('(' + str(line_num) + ',' + str(pos - len(front)) + ')' + ", " + front + text[i][
                    1] + back + "->" + front1 + back1)
            else:
                changes.append('(' + str(line_num) + ',' + str(pos) + ')' + ", " + text[i][1] + "---deleted")

        elif (text[i][0] == -1) and i == 0:
            pos = count_char(-1, i, text)
            if " " in text[i][1] or "\n" in text[i][1]:
                changes.append('(' + str(line_num) + ',' + str(pos) + ')' + ", " + text[i][1] + "---deleted")
            else:
                if front + back != "":
                    check1, back1 = find_back(i, -1, -1, text)
                    changes.append('(' + str(line_num) + ',' + str(pos - len(front)) + ')' + ", " + front + text[i][
                        1] + back + "->" + front + back1)
                else:
                    changes.append('(' + str(line_num) + ',' + str(pos) + ')' + ", " + text[i][1] + "---deleted")

        elif (text[i][0] == -1) and (i + 1 == length):
            pos = count_char(-1, i, text)
            if " " in text[i][1] or "\n" in text[i][1]:
                changes.append('(' + str(line_num) + ',' + str(pos) + ')' + ", " + text[i][1] + "---deleted")
            elif length == 1:
                changes.append('(' + str(line_num) + ',' + str(pos) + ')' + ", " + text[i][1] + "---deleted")
            else:
                check2, front = find_front(i, 1, text)
                if front + back != "":
                    check2, front1 = find_front(i, -1, text)
                    changes.append(
                        '(' + str(line_num) + ',' + str(pos - len(front1)) + ')' + ", " + front1 + text[i][
                            1] + back + "->" + front + back)
                else:
                    changes.append('(' + str(line_num) + ',' + str(pos) + ')' + ", " + text[i][1] + "---deleted")

    for i in range(length):
        front = ""
        back = ""
        if len(text[i]) > 2 or text[i][0] != 1:
            continue
        elif (text[i][0] == 1) and (0 < i < length - 1):
            pos = count_char(1, i, text)
            if i == length - 2 and (
                    text[length - 1][1][0].isspace() or text[length - 1][1][0] == "\n") and revise_word == []:
                changes.append('(' + str(line_num) + ',' + str(pos) + ')' + ", " + text[i][1] + "---added")
            else:
                check1, back = find_back(i, 1, -1, text)
                check2, front = find_front(i, -1, text)
                # debug area
                if (check1 or check2) and (revise_word != []) and (index < len(revise_word)) and (i < len(text)):
                    revise_word[index] += (front + text[i][1] + back)
                    changes.append(revise_word[index])
                    index += 1
                elif front + back != "":
                    check2, front1 = find_front(i, 1, text)
                    check1, back1 = find_back(i, 1, 1, text)
                    changes.append(
                        '(' + str(line_num) + ',' + str(
                            pos - len(front1)) + ')' + ", " + front1 + back1 + "->" + front +
                        text[i][1] + back)
                else:
                    changes.append('(' + str(line_num) + ',' + str(pos) + ')' + ", " + text[i][1] + "---added")

        elif (text[i][0] == 1) and (i == 0):
            pos = count_char(1, i, text)
            if text[i][1][0] == " " or text[i][1][0] == "\n":
                changes.append('(' + str(line_num) + ',' + str(pos) + ')' + ", " +
                               text[i][1] + "---added")
            else:
                check1, back = find_back(i, 1, -1, text)
                if front + back != "":
                    check1, back1 = find_back(i, 1, 1, text)
                    changes.append('(' + str(line_num) + ',' + str(pos - len(front)) + ')' +
                                   ", " + front + back1 + "->" + front + text[i][1] + back)
                else:
                    changes.append('(' + str(line_num) + ',' + str(pos) + ')' + ", " +
                                   text[i][1] + "---added")
        elif (text[i][0] == 1) and (i + 1 == length):
            check, front = find_front(i, -1, text)
            pos = count_char(1, i, text)
            if check:
                revise_word[index] += (front + text[i][1])
                changes.append(revise_word[index])
            elif text[i][1][0] == " " or text[i][1][0] == "\n":
                changes.append('(' + str(line_num) + ',' + str(pos) + ')' + ", " + text[i][1] + "---added")
            elif length == 1:
                changes.append('(' + str(line_num) + ',' + str(pos) + ')' + ", " + text[i][1] + "---added")
            else:
                check2, front = find_front(i, -1, text)
                if front + back != "":
                    check1, back1 = find_back(i, 1, 1, text)
                    changes.append(
                        '(' + str(line_num) + ',' + str(
                            pos - len(front)) + ')' + ", " + front + back + "->" + front +
                        text[i][1] + back1)
                else:
                    changes.append('(' + str(line_num) + ',' + str(pos) + ')' + ", " + text[i][1] + "---added")
    return changes


def tokenize_copy(info):
    text = info['text']
    #debug area
    try:
        clipboard = info['cb']
    except:
        console.log(info)
        clipboard = "No CB Data"
    line_numbers = info['editingLines']
    i = text.find(clipboard)
    char_pos = 0
    line_pos = 0
    for j in range(i, -1, -1):
        if text[j] == '\n':
            line_pos += 1
    for k in range(i - 1, -1, -1):
        if text[k] == '\n':
            break
        char_pos += 1
    info['cb'] = ['(' + str(line_numbers[line_pos]) + ',' + str(char_pos) + ')' + ", " + clipboard]
    return info


def tokenize_revert(info):
    try:
        changes = tokenize_keystroke(info)
        if len(changes) > 1:
            changes = revert_tokenizer(info)
    except:
        changes = revert_tokenizer(info)

    return changes


def revert_tokenizer(info):
    text = ""
    for each in info["revision"]:
        if each[0] == 0 or each[0] == -1:
            text += each[1]
    # pre_text = sentence_reform(text.splitlines(keepends=True))
    # cur_text = sentence_reform(info["text"].splitlines(keepends=True))
    pre_text = sentence_reform(text.splitlines(keepends=True))
    cur_text = sentence_reform(info["text"].splitlines(keepends=True))
    pre = []
    cur = []
    for s in pre_text:
        for each in sent_tokenizer(s).sents:
            pre.extend([str(each)])
    for s in cur_text:
        for each in sent_tokenizer(s).sents:
            cur.extend([str(each)])
    if len(pre) < len(cur):
        change = paste_handler(pre, cur, 1)
    else:
        change = paste_handler(pre, cur, 2)
    if change != "All lines are the same":
        char_num = paste_count_char(info["text"], info["revision"])
        line_num = info['line']
        return ['(' + str(line_num) + ',' + str(char_num) + ') ' + change]
    else:
        return ["All lines are the same"]


def tokenize_paste(info):
    # pre_text = sentence_reform(info["text"].splitlines(keepends=True))
    # cur_text = sentence_reform(info["revision"].splitlines(keepends=True))
    pre_text = info["text"].splitlines(keepends=True)
    cur_text = info["revision"].splitlines(keepends=True)
    # pre_text = info["text"].splitlines()
    # cur_text = info["revision"].splitlines()
    pre = []
    cur = []
    for s in pre_text:
        for each in sent_tokenizer(s).sents:
            pre.extend([str(each)])
    for s in cur_text:
        for each in sent_tokenizer(s).sents:
            cur.extend([str(each)])
    if len(pre) < len(cur):
        change = paste_handler(pre, cur, 1)
    else:
        change = paste_handler(pre, cur, 2)
    if change != "All lines are the same":
        char_num = paste_count_char(info["text"], info["revision"])
        line_num = info['line']
        revision = ['(' + str(line_num) + ',' + str(char_num) + ') ' + change]
    else:
        revision = ["All lines are the same"]

    return revision
