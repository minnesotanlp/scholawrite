let serverURL;
// serverURL = "http://127.0.0.1:5000/"
// serverURL = "http://localhost"
serverURL =  "";
let headers = new Headers();
headers.append('GET', 'POST', 'OPTIONS');
headers.append('Access-Control-Allow-Origin', 'http://127.0.0.1:5000/');
headers.append('Access-Control-Allow-Credentials', 'true');

import { diff_match_patch, DIFF_DELETE, DIFF_INSERT, DIFF_EQUAL } from './diff-match-patch/index.js';
var dmp = diff_match_patch;

let text = [];
let changemade;
let clipboard = "";
let filename = "";
let prelineNumber;
let lineNumber;
let copyLineNumbers;
let projectID = "no url"
let suggestion = ""
let onkey = ""
let username = ""

chrome.storage.local.get(['server'], function(result) {
    if (result.server !== undefined && result.server !== ""){
        serverURL = result.server;
    }
});

chrome.storage.local.get(['username'], function(result) {
    if (result.username !== undefined){
        username = result.username;
    }
});

chrome.runtime.onMessage.addListener(
    function (request, sender, sendResponse) {
        console.log("Entered");
        text = text.filter(function(element) {return element !== undefined;});
        console.log(text);
        projectID = request.project_id
        filename = request.editingFile;
        onkey = request.onkey
        if (request.message == "username"){
            console.log("I got username");
            console.log(request.username);
            username = request.username;
        }
        else if (request.message == "logout"){
            console.log("I got logout");
            username = "";
        }
        else if (request.message == "serverURL"){
            console.log("I got serverURL");
            console.log(request.serverURL);
            serverURL = request.serverURL;
        }
        else if (request.message == "user_selection"){
            var d = new Date();
            var ms = d.getMilliseconds();
            var time = d.toString().slice(0,24)+':'+ms+d.toString().slice(24,);
            if (request.accept == false){
                postWriterText({state: "user_selection", username: username, timestamp: time, accept: false});
            }
            else{
                changemade = difference(request.text, request.revisions);
                postWriterText({state: "user_selection", username: username, timestamp: time, accept: true, project: projectID, file: filename, text: request.revisions, revision: changemade});
                text = [request.revisions];
            }
        }
        else if (request.message == "assist"){
            var d = new Date();
            var ms = d.getMilliseconds();
            var time = d.toString().slice(0,24)+':'+ms+d.toString().slice(24,);
            postWriterText({state: "assist", username: username, timestamp: time, project: projectID, file: filename, pre_content: request.pre_content,
            pos_content: request.pos_content, selected_text: request.selected_text, current_content: request.current_line_content,
            line: request.line});
        }
        if (request.message == "listeners") {
            // process edits, find the diff, as additions or deletions
           console.log("***** press *****");
           text.push(request.text);
           lineNumber = request.start;
           if (prelineNumber == null){
               prelineNumber = request.start;
           }
           if (prelineNumber != lineNumber && lineNumber != null){
               console.log("***** different line *****");
               trackWriterAction(4, text[0], request.text, prelineNumber);
               trackWriterAction(0, request.text, request.revisions, lineNumber);
               prelineNumber = lineNumber
           }
           else{
               trackWriterAction(0, request.text, request.revisions, lineNumber);
               prelineNumber = lineNumber
           }
        }
        else if (request.message == "undo") {
            console.log("***** undo *****");
            text.push(request.text);
            lineNumber = request.start;
            trackWriterAction(0, request.text, request.revisions, lineNumber);
        }
        else if (request.message == "hidden") {
            // process edits, find the diff, as additions or deletions
           console.log("***** hidden *****");
           // text.push(request.text);
           if (text[0] != null && request.revisions != null){
               trackWriterAction(4, text[0], request.revisions, lineNumber);
               prelineNumber = lineNumber
               text = [request.revisions];
           }
        }
        else if (request.message == "scroll"){
            console.log("***** scroll *****");
            if (text[0] !== undefined && text.length > 1){
                console.log(lineNumber)
                trackWriterAction(4, text[0], request.text, lineNumber);
                prelineNumber = null
            }
            text = [request.revisions];
        }
        else if (request.message == "switch"){
            console.log("***** switch *****");
            if (text[0] !== undefined && text.length >= 1){
                console.log(text);
                trackWriterAction(4, text[0], request.text, lineNumber);
                prelineNumber = lineNumber
            }
            text = [request.revisions];
        }
        else if (request.message == "cut") {
            // process edits, find the diff, as additions or deletions
           // text.push(request.text);
           clipboard = request.cutted;
           if(text[0] !== undefined){
            trackWriterAction(4, text[0], request.text, prelineNumber);
           }
           lineNumber = request.start;
           trackWriterAction(1, request.text, request.revisions, lineNumber);
           text = [request.revisions];
        }
        else if (request.message == "copy") {
            // process edits, find the diff, as additions or deletions
           // text.push(request.text);
           clipboard = request.copied;
           if(text[0] !== undefined){
            trackWriterAction(4, text[0], request.text, prelineNumber);
           }
           copyLineNumbers = request.editingLines
           lineNumber = request.start;
           trackWriterAction(2, request.text, request.revisions, lineNumber);
           text = [request.revisions];
        }
        else if (request.message == "paste") {
            // process edits, find the diff, as additions or deletions
           // text.push(request.text);
           console.log("***** paste *****")
           clipboard = request.pasted;
           if(text[0] !== undefined){
            trackWriterAction(4, text[0], request.text, prelineNumber);
           }
           lineNumber = request.start;
           trackWriterAction(3, request.text, request.revisions, lineNumber);
           text = [request.revisions];
        }
         console.log(text);
         sendResponse({message: true});
    }
);

function findLineEdit(editingLines, editingArray, paragraphLines, paragraphArray) {
    if (editingArray.length > paragraphArray.length) {  // line(s) added
        for (let i = 0; i < paragraphArray.length; i++){
            if (paragraphArray[i] != editingArray[i]){
               return (parseInt(paragraphLines[i]) + (editingArray.length - paragraphArray.length))
            }
        }
        console.log(editingLines[editingArray.length - 1])
        return editingLines[editingArray.length - 1]
    } else {
        for (let i = 0; i < editingArray.length; i++){
            if(editingArray[i] != paragraphArray[i]){
               return parseInt(editingLines[i])
            }
        }
        console.log("All lines are the same");
        return prelineNumber
    }
}

function difference(paragraph, revisions) { // utilizing Myer's diff algorithm
    // classifications:
    // 1. addition
    // 2. deletion
    // classification: for swapping texts can be handeled in the back end
    var diff = dmp.prototype.diff_main(
        paragraph,
        revisions);
    // [1: Hello, 1: Goodbye, 0: World];
    // diff = dmp.prototype.diff_cleanupSemantic(diff);
    return diff;
}

// refactor to track writer input
//TODO: support for other actions
function trackWriterAction(state, writerText, revisions, ln) {
    // post comment to the backend
    let change = "addition";
    let diff = difference(writerText, revisions);
    if (diff.length == 0){
     return 0
    }
    var d = new Date();
    var time = d.getTime();
    if (state == 3){
        postWriterText({timestamp: time, username: username, project: projectID, file: filename, text: writerText, revision: revisions,
        state: state, cb: clipboard, line: ln, onkey: onkey})
        text = [revisions]
        clipboard = "";
    }
    else if (diff[0][0] === -1) {
            change = "deletion";
            changemade = difference(text[0], revisions)
            postWriterText({timestamp: time, username: username, project: projectID, file: filename, text: revisions, revision: changemade,
             state: state, cb: clipboard, line: ln, onkey: onkey})
            text = [revisions]
    }
    else if (diff[0][1] === '\n' || diff[0][1] === ' ') {
        change = "addition";
        changemade = difference(text[0], revisions)
        postWriterText({timestamp: time, username: username, project: projectID, file: filename, text: revisions, revision: changemade,
         state: state, cb: clipboard, line: ln, onkey: onkey})
        text = [revisions]
    }
    else if ((diff.length < 2 && diff[0][0] == 0) && (state== 0 || state == 4)) {
        change = "no change";  //TODO: resolve issue, "no change" may also suggest movement to a new line
    }
    else {
        if (state == 1 || state == 2) {
            change = "cut/copy";
            postWriterText({timestamp: time, username: username, project: projectID, file: filename, text: revisions, revision: diff,
            state: state, cb: clipboard, line: ln, copyLineNumbers:copyLineNumbers, onkey: onkey})
            text = [revisions]
            clipboard = "";
        }
        else if(diff[0][0] === 1 && state == 4) {
            change = "addition";
            changemade = difference(writerText, revisions)
            postWriterText({timestamp: time, username: username, project: projectID, file: filename, text: revisions, revision: changemade,
            state: state, cb: clipboard, line: ln, onkey: onkey})
        }
        else if(diff[1][0] === -1) {
            change = "deletion";

            if ((diff[1][1].includes('\n') || diff[1][1].includes(' '))|| state != 0 || diff.length > 3){
               // if user delete a space, the chars array will be send to the backend for processing
                changemade = difference(text[0], revisions)
                postWriterText({timestamp: time, username: username, project: projectID, file: filename, text: revisions, revision: changemade,
                state: state, cb: clipboard, line: ln, onkey: onkey})
                text = [revisions]
            }
        }
        else if (diff[1][0] === 1){
            change = "addition";
            if ((diff[1][1].includes('\n') || diff[1][1].includes(' ')) || state != 0 || diff.length > 3){
                // if user add a space, the chars array will be send to the backend for processing
                changemade = difference(text[0], revisions)
                postWriterText({timestamp: time, username: username, project: projectID, file: filename, text: revisions, revision: changemade,
                state: state, cb: clipboard, line: ln, onkey:onkey})
                text = [revisions]
            }
        }
    }
}


async function postWriterText(activity) {
    console.log(activity);
    try {
        const response = await fetch(serverURL + "/ReWARD/activity", {
            // mode: 'no-cors',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            method: 'POST',
            body: JSON.stringify(activity),
        })
        const message = await response.json();
        console.log(message);
        if (response.ok && message.status == "ChatGPT"){
            chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
                chrome.tabs.sendMessage(tabs[0].id, {source: "chatgpt", suggestion: message.suggestion, same_line_before: message.same_line_before, same_line_after: message.same_line_after, diffs_html: message.diffs_html, explanation: message.explanation}, function (response) {
                });
            });
        }
    }
    catch (err){
        console.log('failed to fetch');
    }
}

//async function generateText(activity) {
//    console.log(activity);
//    const response = await fetch(serverURL + "/ReWARD/activity", {
//        mode: 'no-cors',
//        headers: {
//            'Accept': 'application/json',
//            'Content-Type': 'application/json'
//        },
//        method: 'GET',
//        body: JSON.stringify(activity),
//    }, async function (err, resp, body) {
//        console.log("from main.py:");
//        const message = await resp.json();
//        console.log("from main.py:",message.status);
//        chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
//            chrome.tabs.sendMessage(tabs[0].id, {source: "chatgpt", suggestion: message.status, same_line_before: message.same_line_before, same_line_after: message.same_line_after, diffs_html: message.diffs_html}, function (response) {
//            });
//        });
//    });
//    return true;
//}