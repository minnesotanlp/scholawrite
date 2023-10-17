function getEditingText() { // find areas in current file that reader may be reading
    editingParagraph = "";
    editingLines = [];
    let textarea = document.getElementsByClassName("cm-content cm-lineWrapping")[0];
    lineArea = document.getElementsByClassName("cm-gutter cm-lineNumbers")[0].childNodes;

    // Determine whether active line is visible. If count equal to three, active line is NOT visible
    var elements = textarea.querySelectorAll('div[contenteditable="false"][style]');
    var count = elements.length;

    lines = textarea.childNodes;
    var length = lineArea.length;
    var k = 1
    var offset = 0

    if (lines[1].nextElementSibling != null && lines[1].nextElementSibling.matches('div[contenteditable="false"][style]')){
        k = count
        offset = count - 1
        length = length + offset
    }
    else{
        count = 1
    }
    for (; k < length; k++){
        line = lines[k].innerText;
        if(line === "\n"){
           line = "";
        }
        if(k > count){
            line = "\n"+line;
        }
        editingParagraph += line;
        editingLines.push(lineArea[k - offset].textContent);
    }

    editingParagraph = editingParagraph.replace(reg1, '\\author{anonymous}');
    editingParagraph = editingParagraph.replace(reg2, '\\affil{anonymous}');
    destroy();

    return;
}


chrome.runtime.onMessage.addListener(
    function(request, sender, sendResponse) {
        if (request.source == "chatgpt"){
            clearTimeout(timeout);
            console.log(request)
            paraphrase = request.suggestion;
            explanation = request.explanation
            same_line_before = request.same_line_before;
            same_line_after = request.same_line_after;

            // tpcontent stands for tooltip content. It is ChatGPT generated.
            // diffs_html showing the difference between User's writing and ChatGPT's paraphrasing
            if (paraphrase == ""){
                var divToRemove = tooltip.getElementsByClassName('loader');
                var styleToRemove = tooltip.querySelector('style');
                tooltip.removeChild(divToRemove[0]);
                styleToRemove.innerHTML = '';
                tooltip.textContent = "Sorry, a server error encountered. Please try again later.";
                document.addEventListener('click', tooltipClickRemove);
            }
            else if (explanation == ""){
                tooltip.parentNode.removeChild(tooltip);
                tooltip = null;
                document.removeEventListener('click', tooltipClick);
                var rightPanel = document.querySelector(".ui-layout-east.ui-layout-pane.ui-layout-pane-east")
                var extensionURL = chrome.runtime.getURL('tooltip.html');
                var time = (new Date()).toString().slice(0,21);
                tooltip = document.createElement('aside')
                tooltip.className = "Chat"
                fetch(extensionURL)
                    .then(response => response.text())
                    .then(htmlContent => {
                        tooltip.innerHTML = htmlContent;
                        tooltip.querySelector('.date').textContent = time;
                        tooltip.querySelectorAll('.message-content')[0].innerHTML = request.diffs_html;
                        tooltip.querySelectorAll('.message-content')[1].textContent = "Sorry, ChatGPT didn't provide any explanation for this paraphrased text.";
                        rightPanel.appendChild(tooltip);
                        tooltip.querySelector('.accept-button').addEventListener('click', tooltipClick);
                        tooltip.querySelector('.reject-button').addEventListener('click', tooltipClick);
                    })
            }
            else{
                tooltip.parentNode.removeChild(tooltip);
                tooltip = null;
                document.removeEventListener('click', tooltipClick);
                var rightPanel = document.querySelector(".ui-layout-east.ui-layout-pane.ui-layout-pane-east")
                var extensionURL = chrome.runtime.getURL('tooltip.html');
                var time = (new Date()).toString().slice(0,21);
                tooltip = document.createElement('aside')
                tooltip.className = "Chat"
                fetch(extensionURL)
                    .then(response => response.text())
                    .then(htmlContent => {
                        tooltip.innerHTML = htmlContent;
                        tooltip.querySelector('.date').textContent = time;
                        tooltip.querySelectorAll('.message-content')[0].innerHTML = request.diffs_html;
                        tooltip.querySelectorAll('.message-content')[1].textContent = explanation;
                        rightPanel.appendChild(tooltip);
                        tooltip.querySelector('.accept-button').addEventListener('click', tooltipClick);
                        tooltip.querySelector('.reject-button').addEventListener('click', tooltipClick);
                    })
            }
        }
    }
);

function createTooltip(){
    tooltip = document.createElement('div');
    tooltip.style.position = 'fixed';
    tooltip.style.top =  tptop + 'px';
    tooltip.style.left = tpleft + 'px';
    tooltip.style.border = '1px solid black';
    tooltip.style.padding = '5px';
    tooltip.style.backgroundColor = '#FFF8DC';
    tooltip.innerHTML = `
 <div class="loader"></div>
  Please wait, ChatGPT is processing...
  <style>
  .loader {
    border: 8px solid #ABB2B9;
    border-top: 8px solid #3498db;
    border-radius: 50%;
    width: 40px;
    height: 40px;
    animation: spin 1s linear infinite;
    margin: auto;
  }

  @keyframes spin {
    0% {
      transform: rotate(0deg);
    }
    100% {
      transform: rotate(360deg);
    }
  }
  </style>
</div>`;
    document.body.appendChild(tooltip);
}

function AI_Paraphrase(){
    // get selected information such as html element, text, and position relative to viewers' screen
    try {
        var selected_element = window.getSelection();
        var selected_text = selected_element.toString();
        var selected_range = selected_element.getRangeAt(0); //get the text range
        var selected_pos = selected_range.getBoundingClientRect();
    }
    catch(err){
        console.log("You are not selecting any text!");
        return;
    }
    // get all the lines and number of lines
    const cm_content = document.getElementsByClassName("cm-content cm-lineWrapping");
    console.log(selected_text);
    console.log("--------------------------------");
    lines = cm_content[0].childNodes;
    var length = lines.length;
    console.log(length);
    console.log(selected_range);

    var startContainer = selected_range.startContainer
    while(startContainer.className !== "cm-line"){
        startContainer = startContainer.parentElement
    }
    var endContainer = selected_range.endContainer
    while(endContainer.className !== "cm-line"){
        endContainer = endContainer.parentElement
    }
    console.log(startContainer);
    console.log(endContainer);
    console.log("--------------------------------");
    console.log(selected_pos);
    var found_range = undefined;        // The range object of selected elements
    var DOMRectArray = [];              // An DOMRect object array. DOMRect: the size and position of an element
    var num_of_rows = 0;                // Number of rows of selected text in Latex editor
    var i = 1;                          // loop variable
    start = 0;                      // startContainer's position
    end = 0;                        // endContainer's position
    var skipCheck = 0;                  // Whether found the position of startContainer
    var breakCheck = 0;                 // Whether found the Position of endContainer

    // algorithm to get the selected line.
    // This could help us get the context and feed into ChatGPT
    var countStart = 0
    var countEnd = 0
    var textArray = []
    for (; i<length; i++){
        line = lines[i].innerText;
        if (line !== '\n'){
            textArray.push(line);
        }
        else{
            textArray.push('');
        }
        if (line === startContainer.innerText){
            countStart += 1
        }
        // the start and end text could be the same
        if (line ===  endContainer.innerText){
            countEnd += 1
        }
    }

    console.log("countStart: ",countStart)
    console.log("countEnd: ",countEnd)
    for (i=1; i<length; i++){
        line = lines[i].innerText;
        console.log(line);
        if (skipCheck == 0 && line === startContainer.innerText){
            console.log("here");
            found_range = lines[i].ownerDocument.createRange();
            found_range.selectNodeContents(lines[i]);

            DOMRectArray = Array.from(found_range.getClientRects())
            num_of_rows = DOMRectArray.length / countEnd
            if (DOMRectArray.slice(start, start + num_of_rows).some((rec) => rec.top.toFixed(3) === selected_pos.top.toFixed(3))){
                // reassign "start". Now "start" is no longer a loop variable but start position of selection
                start = i
                skipCheck = 1;
            }
            else{
                start = start + num_of_rows
            }
        }
        if (skipCheck == 1 && line === endContainer.innerText){
            console.log("here2");
            found_range = lines[i].ownerDocument.createRange();
            found_range.selectNodeContents(lines[i]);

            DOMRectArray = Array.from(found_range.getClientRects())
            num_of_rows = DOMRectArray.length / countEnd
            console.log(DOMRectArray, num_of_rows)
            if (DOMRectArray.slice(end, end + num_of_rows).some((rec) => rec.bottom.toFixed(3) === selected_pos.bottom.toFixed(3))){
                 // reassign "end". Now "end" is no longer a loop variable but start position of selection
                end = i
                breakCheck = 1;
                break;
            }
            else{
                end = end + num_of_rows;
            }
        }
    }
    console.log(start)
    console.log(end)
    lineNumbers = lineArea[start].innerText + " - "+ lineArea[end].innerText
    console.log(lineNumbers)
    pre_content = textArray.slice(0, start - 1).join('\n')
    selected_lines = textArray.slice(start - 1, end).join('\n')
    pos_content = textArray.slice(end).join('\n')
    console.log([textArray.slice(0, start - 1).join('\n')]);
    console.log([textArray.slice(start - 1, end).join('\n')]);
    console.log([textArray.slice(end).join('\n')]);
    pre_content = pre_content.replace(reg1, '\\author{anonymous}');
    pre_content = pre_content.replace(reg2, '\\affil{anonymous}');
    pos_content = pos_content.replace(reg1, '\\author{anonymous}');
    pos_content = pos_content.replace(reg2, '\\affil{anonymous}');
    selected_lines = selected_lines.replace(reg1, '\\author{anonymous}');
    selected_lines = selected_lines.replace(reg2, '\\affil{anonymous}');

    tptop = selected_pos.y + selected_pos.height;
    tpleft = selected_pos.x + selected_pos.width;
    createTooltip();

    chrome.runtime.sendMessage({editingFile: filename,message: "assist", pre_content: pre_content, pos_content: pos_content,
    selected_text: selected_text, current_line_content: selected_lines, project_id: project_id, line: lineNumbers});

    timeout = setTimeout(function() {
        var divToRemove = tooltip.getElementsByClassName('loader');
        var styleToRemove = tooltip.querySelector('style');
        tooltip.removeChild(divToRemove[0]);
        styleToRemove.innerHTML = '';
        tooltip.textContent = "Sorry, a server error encountered. Please try again later.";
        document.addEventListener('click', tooltipClickRemove);
    }, 15000);
}

// The tooltip disappears no matter where the user clicks
function tooltipClickRemove(){
    tooltip.parentNode.removeChild(tooltip);
    tooltip = null;
    document.removeEventListener('click', tooltipClickRemove);
    chrome.runtime.sendMessage({message: "user_selection", accept: false});
}

//Replace text if user click inside the tooltip; remove the tooltip if user clicks outside it
function tooltipClick(event) {
    if (event.target === tooltip.querySelector('.reject-button')) {
        tooltip.removeEventListener('click', tooltipClick);
        tooltip.parentNode.removeChild(tooltip);
        tooltip = null;
        chrome.runtime.sendMessage({message: "user_selection", accept: false});
    }
    else if (event.target === tooltip.querySelector('.accept-button')){
        console.log("1: ",same_line_before);
        console.log("2: ",paraphrase);
        console.log("3: ",same_line_after);
        var startIndex;
        var endIndex;
        var substring;
        var string = same_line_before + paraphrase + same_line_after;
        var num_of_replace_line = end - start + 1
        // Calculate the desired length of each substring
        var substringLength = Math.ceil(string.length / num_of_replace_line);
        // assign each substring to each line
        for (let i = 0; i < num_of_replace_line; i++) {
            startIndex = i * substringLength;
            endIndex = startIndex + substringLength;
            lines[start+i].innerText = string.substring(startIndex, endIndex);
        }

        tooltip.parentNode.removeChild(tooltip);
        tooltip = null;
        getEditingText();
        document.removeEventListener('click', tooltipClick);
        chrome.runtime.sendMessage({editingFile: filename, message: "user_selection", accept: true, revisions: editingParagraph, text: paragraph, editingLines: editingLines, editingArray: editingArray, paragraphLines: paragraphLines, paragraphArray: paragraphArray, project_id: project_id});
        paragraph = editingParagraph;
        paragraphArray = editingArray;
        paragraphLines = editingLines;
    }
}

window.addEventListener("load", async function(){
    editor = document.getElementsByClassName("editor")[0];
    console.log(editor);
    // if the ditor is undefined, means we are not in the editor page
    if (editor === undefined){
        console.log("not in editor");
        return;
    }
    let loadNode = document.getElementsByClassName("loading-panel ng-hide")[0];
    while (loadNode == undefined) {
        console.log("loading")
        await sleep(100); // Adjust the delay time as needed
        loadNode = document.getElementsByClassName("loading-panel ng-hide")[0];
    }
    await sleep(100);

    // Add an AI paraphrase botton
    var toolbarRight = document.querySelector('.toolbar-right');
    var AI_Paraphrase_button = document.createElement('div')
    AI_Paraphrase_button.className = "toolbar-item"
    AI_Paraphrase_button.innerHTML = `<button class= "btn btn-full-height"><p class= toolbar-label>AI Paraphrase</p></button>`;
    console.log(AI_Paraphrase_button);
    var onlineUsers = toolbarRight.querySelector('.online-users');
    toolbarRight.insertBefore(AI_Paraphrase_button, onlineUsers.nextSibling);
    AI_Paraphrase_button.addEventListener('click', AI_Paraphrase)

})
