let paragraph = "";
let editingParagraph = "";
let state = 0;
let pasteData = "";
let clipboard = "";
let project_id = "";
const reg1 = /(\\author(?:\[(\d*)\])*{+[^}\n\\]+}*)/g;
const reg2 = /(\\affil(?:\[(\d*)\])*{+[^}\n\\]+}*)/g;
let file;
let filename;
let lineArea;
let fileObserver;

let paragraphLines = [];
let editingLines = [];

let tooltip = null;
let tptop = null;
let tpleft = null
let lines = null;
let start = 0;
let end = 0;
let same_line_before = ""
let same_line_after = ""

let EXTENSION_TOGGLE = false;
let paraphrase = "Hello, This is a tooltip!"

let timeout;
let assist_lines;
let username = "";

let clipboardData = "";

chrome.runtime.onMessage.addListener(
    function(request, sender, sendResponse) {
        if (request.source == "chatgpt"){
            assist_lines= request.line;
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
        else if(request.source == "username"){
            username = request.username;
        }
        else{
            EXTENSION_TOGGLE = request.toggle
            if (request.toggle) {
                getEditingText();
                paragraph = editingParagraph;
                paragraphLines = editingLines;
                console.log("CONTENT ON");
            } else {
                console.log("CONTENT OFF");
                chrome.runtime.sendMessage({username: username, message: "CONTENT OFF"});
            }
        }
         sendResponse({message: true});
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
        alert("You are not selecting any text!");
        return;
    }
    if (selected_text == ""){
        alert("You are not selecting any text!");
        return;
    }
    else if(EXTENSION_TOGGLE == false){
        alert("Your extension toggle is off!");
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

    const cmLines = document.querySelectorAll(".cm-gutter.cm-lineNumbers > .cm-gutterElement");
    var tempLines = Array.from(cmLines);
    var tempLineNums = tempLines.map(element => element.textContent);
    editingLines = tempLineNums.slice(1);

    chrome.runtime.sendMessage({username: username, editingFile: filename,message: "assist", pre_content: pre_content, pos_content: pos_content,
    selected_text: selected_text, current_line_content: selected_lines, project_id: project_id, line: lineNumbers, editingLines: editingLines});

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
    sendUserChoiceToBackground(false, assist_lines, 1)
}

//Replace text if user click inside the tooltip; remove the tooltip if user clicks outside it
function tooltipClick(event) {
    if (event.target === tooltip.querySelector('.reject-button')) {
        tooltip.removeEventListener('click', tooltipClick);
        tooltip.parentNode.removeChild(tooltip);
        tooltip = null;
        sendUserChoiceToBackground(false, assist_lines)
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
        sendUserChoiceToBackground(true, assist_lines)
        paragraph = editingParagraph;
        paragraphLines = editingLines;
    }
}

function sendUserChoiceToBackground(accept, assist_lines, error){
    project_id = document.querySelector('meta[name="ol-project_id"]').content;
    getEditingText();
    file = document.querySelector('[role = "treeitem"][aria-selected = "true"]');
    filename = file.getAttribute("aria-label");
    if(accept == false){
        chrome.runtime.sendMessage({username: username, editingFile: filename, message: "user_selection", assistError: error, accept: accept, revisions: editingParagraph, text: editingParagraph, editingLines: editingLines, project_id: project_id, start: assist_lines});
    }
    else{
        chrome.runtime.sendMessage({username: username, editingFile: filename, message: "user_selection", accept: accept, revisions: editingParagraph, text: paragraph, editingLines: editingLines, project_id: project_id, start: assist_lines});
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
    paragraph = "";
    paragraphLines = [];
    let loadNode = document.getElementsByClassName("cm-gutter cm-lineNumbers")[0];
    while (loadNode == null) {
        console.log("loading")
        await sleep(100); // Adjust the delay time as needed
        loadNode = document.getElementsByClassName("cm-gutter cm-lineNumbers")[0];
    }
    let textarea = document.getElementsByClassName("cm-content cm-lineWrapping");
    lineArea = loadNode.childNodes;
    // Add event listeners to detect user undo/redo action
    var inputElements = document.querySelectorAll(".cm-content.cm-lineWrapping");
    inputElements[0].addEventListener("beforeinput", function(event) {
        checkUndoOrRevert(inputElements, event);
    });

    lines = textarea[0].childNodes;
    var length = lineArea.length;
    console.log("textlen", lines.length)
    console.log("linelen", length)
    for (var k = 1; k < length; k++) {
        line = lines[k].innerText;
        if(line === "\n"){
           line = "";
        }
        if(k > 1){
            line = "\n"+line;
        }
        paragraph += line;
        paragraphLines.push(lineArea[k].textContent);
    }
    paragraph = paragraph.replace(reg1, '\\author{anonymous}');
    paragraph = paragraph.replace(reg2, '\\affil{anonymous}');

    console.log(paragraph)
    console.log(paragraphLines)

    //Get project ID, valid for both legacy and non-legacy
    project_id = document.querySelector('meta[name="ol-project_id"]').content;
    file = document.querySelector('[role = "treeitem"][aria-selected = "true"]');
    filename = file.getAttribute("aria-label");
    console.log("load");
    chrome.storage.local.get('enabled', function (result) {
        var checking = false
        if (result.enabled != null) {
            checking = result.enabled;
        }
        if (checking){
            EXTENSION_TOGGLE = true
        }
        else if (!checking){
            destroy();
        }
    })

    chrome.storage.local.get(['username'], function(result) {
        if (result.username !== undefined || result.username !== ""){
            username = result.username;
        }
    });

    // tell background to set certain variables to default
    chrome.runtime.sendMessage({username: username, editingFile: filename, message: "Load", text: paragraph, project_id: project_id, editingLines: paragraphLines});

    // switch document mutation observer setup
    fileObserver = new MutationObserver(filePost);
    const fileConfig = {attributeFilter: ["aria-selected", "selected"]};
    fileObserver.observe(file, fileConfig);

    // scroll mutation observer setup
    let scrollNode = null;
    let scrollConfig = null;
    //scrollNode = document.getElementsByClassName('cm-content cm-lineWrapping')[0];
    scrollNode = document.getElementsByClassName('cm-gutterElement')[1];
    console.log(scrollNode);
    scrollConfig = {attributeFilter: ["style"], attributeOldValue: true};
    const scrollObserver = new MutationObserver(scrollPost);
    scrollObserver.observe(scrollNode, scrollConfig);

    // Add an AI paraphrase botton
    var toolbarRight = document.querySelector('.toolbar-right');
    var AI_Paraphrase_button = document.createElement('div')
    AI_Paraphrase_button.className = "toolbar-item"
    AI_Paraphrase_button.innerHTML = `<button class= "btn btn-full-height"><p class= toolbar-label>AI Paraphrase</p></button>`;
    console.log(AI_Paraphrase_button);
    var onlineUsers = toolbarRight.querySelector('.online-users');
    toolbarRight.insertBefore(AI_Paraphrase_button, onlineUsers.nextSibling);
    AI_Paraphrase_button.addEventListener('click', AI_Paraphrase)

    document.querySelector('[aria-label="Undo"]').addEventListener('click', function(){setTimeout(sendUndoRedo, 100)});
    document.querySelector('[aria-label="Redo"]').addEventListener('click', function(){setTimeout(sendUndoRedo, 100)});
});

function sendToBackground(message, onkey = ""){
    project_id = document.querySelector('meta[name="ol-project_id"]').content;
    getEditingText();
    var start = getActiveLine();
    file = document.querySelector('[role = "treeitem"][aria-selected = "true"]');
    filename = file.getAttribute("aria-label");
    if (EXTENSION_TOGGLE) {
        if (![1, 2, 3].includes(state)){
            console.log({editingFile: filename, message: message, revisions: editingParagraph, text: paragraph, editingLines: editingLines, paragraphLines: paragraphLines, project_id: project_id, onkey: onkey, start: lineArea[start].innerText});
            chrome.runtime.sendMessage({username: username, editingFile: filename, message: message, revisions: editingParagraph, text: paragraph, editingLines: editingLines, paragraphLines: paragraphLines, project_id: project_id, onkey: onkey, start: lineArea[start].innerText});
        }
        else{
            console.log({editingFile: filename, message: message, revisions: editingParagraph, text: paragraph, clipboardData: clipboardData, editingLines: editingLines, project_id: project_id, onkey: onkey, start: lineArea[start].innerText});
            chrome.runtime.sendMessage({username: username, editingFile: filename, message: message, revisions: editingParagraph, text: paragraph, clipboardData: clipboardData, editingLines: editingLines, project_id: project_id, onkey: onkey, start: lineArea[start].innerText});
        }
    }
    state = 0;
    paragraph = editingParagraph;
    paragraphLines = editingLines;
    destroy();
}

function getEditingText() { // find areas in current file that reader may be reading
    editingParagraph = "";
    editingLines = [];
    lineArea = document.getElementsByClassName("cm-gutter cm-lineNumbers")[0].childNodes;

    const cmContent = document.querySelectorAll(".cm-content.cm-lineWrapping > .cm-line");
    const cmLines = document.querySelectorAll(".cm-gutter.cm-lineNumbers > .cm-gutterElement");
    var tempLines = Array.from(cmLines);
    var offset = 0;
    for (let i = 0; i<cmContent.length; i++){
        if (cmContent[i].className == "cm-activeLine cm-line" && (tempLines.slice(1))[i-offset]?.className != "cm-gutterElement cm-activeLineGutter"){
            console.log(cmContent[i]);
            console.log(tempLines.slice(1)[i-offset]);
            offset += 1;
            continue;
        }
        else if (cmContent[i].previousElementSibling?.matches('div[contenteditable="false"][style]') && cmContent[i].nextElementSibling?.matches('div[contenteditable="false"][style]')){
            offset += 1;
            continue;
        }
        line = cmContent[i].innerText;
        if(line === "\n"){
           line = "";
        }
        if(i > offset){
            line = "\n"+line;
        }
        editingParagraph += line;
    }
    var tempLineNums = tempLines.map(element => element.textContent);
    editingLines = tempLineNums.slice(1);
    console.log(paragraph);
    console.log(editingParagraph);
    editingParagraph = editingParagraph.replace(reg1, '\\author{anonymous}');
    editingParagraph = editingParagraph.replace(reg2, '\\affil{anonymous}');
    destroy();

    return;
}

function getActiveLine(){
    // get selected information such as html element, text, and position relative to viewers' screen
    var selected_element = window.getSelection();
    var selected_range = selected_element.getRangeAt(0); //get the text range

    var startContainer = selected_range.startContainer;
    while((startContainer?.className) !== "cm-line" && (startContainer?.className) !== "cm-activeLine cm-line"){
        startContainer = startContainer.parentElement
    }
    var parent = startContainer.parentElement
    var lineNumber = Array.from(parent.children).indexOf(startContainer);
    return lineNumber;
}

// if user leave the current page, send Message to background.
document.addEventListener("visibilitychange", () => {
    setTimeout(() => {
        if (document.visibilityState === 'hidden') {
            if (EXTENSION_TOGGLE) {
                chrome.runtime.sendMessage({username: username, message: "Hidden", revisions: editingParagraph, text: paragraph, onkey: "", editingLines: editingLines, project_id: project_id});
            }
        }
    }, 0)
});


function scrollPost(mutations){
    console.log(mutations)
    console.log("***** scroll *****")
    project_id = document.querySelector('meta[name="ol-project_id"]').content;
    file = document.querySelector('[role = "treeitem"][aria-selected = "true"]');
    filename = file.getAttribute("aria-label");
    getEditingText();
    chrome.runtime.sendMessage({username: username, editingFile: filename, message: "Scroll", revisions: editingParagraph, text: paragraph, editingLines: editingLines, paragraphLines: paragraphLines, project_id: project_id, onkey: ""});
    paragraph = editingParagraph;
    paragraphLines = editingLines;
    destroy();
}


function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function filePost(){
    fileObserver.disconnect();
    file = document.querySelector('[role = "treeitem"][aria-selected = "true"]');
    console.log(file);
    f = file.getAttribute("aria-label");
    console.log(f);

    let loadNode = document.getElementsByClassName("loading-panel ng-hide")[0];
    while (loadNode == undefined) {
        console.log("loading")
        await sleep(100); // Adjust the delay time as needed
        loadNode = document.getElementsByClassName("loading-panel ng-hide")[0];
    }
    sendToBackground("Switch")
    fileObserver.observe(file, {attributeFilter: ["aria-selected", "selected"]});

    document.querySelector('[aria-label="Undo"]').addEventListener('click', function(){setTimeout(sendUndoRedo, 100)});
    document.querySelector('[aria-label="Redo"]').addEventListener('click', function(){setTimeout(sendUndoRedo, 100)});
}

function sendUndoRedo(){
    console.log("click undo redo");
    sendToBackground("Undoredo");
}

window.addEventListener('beforeunload', function(event) {
    event.preventDefault();
    chrome.runtime.sendMessage({username: username, message: "Unload", editingLines: editingLines});
});

document.body.addEventListener('cut', (event) => {
    state = 1;
    console.log('***** cut ****');
    clipboard = event.clipboardData || window.clipboardData;
    clipboardData = clipboard.getData('Text');
    sendToBackground("Cut");
});

document.body.addEventListener('copy', (event) => {
    state = 2;
    console.log('***** copy ****');
    clipboard = event.clipboardData || window.clipboardData;
    clipboardData = clipboard.getData('Text');
    sendToBackground("Copy");
});

document.body.addEventListener('paste', (event) => {
    state = 3
    console.log('***** paste ****');
    clipboard = event.clipboardData || window.clipboardData;
    clipboardData = clipboard.getData('Text');
    sendToBackground("Paste");
});

let excludedKeys = ["Meta", "Alt", "Tab","Shift","CapsLock","ArrowUp", "Control", "ArrowDown", "ArrowLeft","ArrowRight"];

document.body.onkeyup = function (e) { // save every keystroke
    if (!excludedKeys.includes(e.key)){
        onkey = e.key;
        sendToBackground("Typing", onkey);
    }
}

function checkUndoOrRevert(element, event) {
    if (event.inputType === "historyUndo" || event.inputType === "historyRedo") {
        sendToBackground("Undoredo");
    }
}

function destroy() {
    if (!EXTENSION_TOGGLE) {
        paragraph = "";
        editingParagraph = "";
        project_id = ""
        paragraphLines = [];
        editingLines = [];
    }
}