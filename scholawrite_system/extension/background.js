let serverURL;
//serverURL =  "http://127.0.0.1:5000";
serverURL = "https://scholawrite.ngrok.app/";
let headers = new Headers();
headers.append('GET', 'POST', 'OPTIONS');
//headers.append('Access-Control-Allow-Origin', 'http://127.0.0.1:5000/');
headers.append('Access-Control-Allow-Origin', 'https://scholawrite.ngrok.app/');
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
let projectID = "no url";
let suggestion = "";
let onkey = "";
let username = "";
let editingLines = "";
let action = ""


chrome.runtime.onMessage.addListener(
    function (request, sender, sendResponse) {
        text = text.filter(function(element) {return element !== undefined;});
        console.log(request);
        projectID = request.project_id;
        filename = request.editingFile;
        onkey = request.onkey;
        editingLines = request.editingLines;
        action = request.message;
        username = request.username;
        if (request.message == "user_selection"){
            var d = new Date();
            var time = d.getTime();

            text = [request.revisions];
            // Add diff array and delete revisions
            // from request that going to send to the server
            let writableRequest = request;
            let changeMade = difference(request.text, request.revisions);
            writableRequest["revision"] = changeMade;
            writableRequest.text = request.revisions
            delete request.revisions

            request.timestamp = time;
            if (request.accept == false){
                postParaphraseText(writableRequest);
            }
            else{
                postParaphraseText(writableRequest);
            }
        }
        else if (request.message == "assist"){
            var d = new Date();
            var time = d.getTime();
            postParaphraseText({message: "assist", username: request.username, timestamp: time, project: projectID, file: filename, pre_content: request.pre_content,
            pos_content: request.pos_content, selected_text: request.selected_text, current_content: request.current_line_content,
            line: request.line}, sender.tab.id);
        }
        if (request.message == "Typing") {
            // process edits, find the diff, as additions or deletions
           console.log("***** typing *****");
           lineNumber = request.start;
           // In the very beginning of writing, prelineNumber doesn't have a value.
           // Therefore, we assign current active line number to it
           if (prelineNumber == null){
               prelineNumber = request.start;
           }
           if (text.length == 0){
            text.push(request.text);
           }
           text.push(request.revisions);
           // if user is editing on different line, we record writer action. If not, we keep tracking user's writing.
           if (prelineNumber != lineNumber && lineNumber != null){
               console.log("***** different line *****");
               trackWriterAction(4, text[0], request.text, prelineNumber);
               trackWriterAction(0, request.text, request.revisions, lineNumber);
               prelineNumber = lineNumber
           }
           else if (text.length > 40){
                console.log("***** reach array max *****");
                trackWriterAction(4, text[0], request.revisions, lineNumber);
                prelineNumber = lineNumber
           }
           else{
               trackWriterAction(0, request.text, request.revisions, lineNumber);
               prelineNumber = lineNumber
           }
        }
        else if (request.message == "Load"){
            console.log("load");
            if (text.length == 0){
                text = [request.text];
            }
        }
        else if (request.message == "Unload"){
           console.log("unload");
           onkey = "";
           if (text.length >= 2){
               trackWriterAction(4, text[0], text.at(-1), prelineNumber);
           }
           text = [];
           prelineNumber = null;
        }
        else if (request.message == "Undoredo") {
            console.log("***** undo *****");
            text.push(request.text);
            lineNumber = request.start;
            trackWriterAction(4, request.text, request.revisions, lineNumber);
        }
        else if (request.message == "Hidden") {
            // process edits, find the diff, as additions or deletions
           console.log("***** hidden *****");
           var temp = "";
           if (request.revisions != ''){
                temp = request.revisions;
           }
           else{
                temp = request.text;
           }
           if (text[0] != null && temp != ''){
               trackWriterAction(4, text[0], temp, lineNumber);
               prelineNumber = lineNumber
           }
        }
        else if (request.message == "Scroll"){
            console.log("***** scroll *****");
            if (text[0] !== undefined && text.length > 1){
                trackWriterAction(4, text[0], request.text, lineNumber);
                prelineNumber = null
            }
            text = [request.revisions];
        }
        else if (request.message == "Switch"){
            console.log("***** switch *****");
            if (text[0] !== undefined && text.length >= 1){
                trackWriterAction(4, text[0], request.text, lineNumber);
            }
            text = [request.revisions];
            prelineNumber = null;
        }
        else if (request.message == "Cut") {
            // process edits, find the diff, as additions or deletions
           // text.push(request.text);
           clipboard = request.clipboardData;
           if(text[0] !== undefined){
            trackWriterAction(4, text[0], request.text, prelineNumber);
           }
           lineNumber = request.start;
           trackWriterAction(1, request.text, request.revisions, lineNumber);
           text = [request.revisions];
        }
        else if (request.message == "Copy") {
            // process edits, find the diff, as additions or deletions
           // text.push(request.text);
           clipboard = request.clipboardData;
           if(text[0] !== undefined){
            trackWriterAction(4, text[0], request.text, prelineNumber);
           }
           copyLineNumbers = request.editingLines
           lineNumber = request.start;
           trackWriterAction(2, request.text, request.revisions, lineNumber);
           text = [request.revisions];
        }
        else if (request.message == "Paste") {
            // process edits, find the diff, as additions or deletions
           // text.push(request.text);
           console.log("***** paste *****")
           clipboard = request.clipboardData;
           if(text[0] !== undefined){
            trackWriterAction(4, text[0], request.text, prelineNumber);
           }
           lineNumber = request.start;
           trackWriterAction(3, request.text, request.revisions, lineNumber);
           text = [request.revisions];
        }
        else if (request.message == "CONTENT OFF"){
            text = [];
            prelineNumber = null;
        }
         sendResponse({message: true});
    }
);


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
        changemade = difference(writerText, revisions);
        postWriterText({timestamp: time, text: writerText, revision: revisions, changemade: changemade, state: state, cb: clipboard, line: ln})
        text = [revisions]
        clipboard = "";
    }
    else if (diff[0][0] === -1) {
            change = "deletion";
            changemade = difference(text[0], revisions)
            // if incomplete word is written and deleted, we won't do anything
            if (changemade.length > 0){
                postWriterText({timestamp: time, text: revisions, revision: changemade, state: state, line: ln})
            }
            text = [revisions]
    }
    else if (diff[0][1] === '\n' || diff[0][1] === ' ') {
        change = "addition";
        changemade = difference(text[0], revisions)
        postWriterText({timestamp: time, text: revisions, revision: changemade, state: state, line: ln})
        text = [revisions]
    }
    // when undo and redo at the beginning of text
    else if (diff[0][0] === 1 && (diff[0][1].includes('\n') || diff[0][1].includes(' '))){
            change = "addition";
            changemade = difference(text[0], revisions)
            postWriterText({timestamp: time, text: revisions, revision: changemade, state: state, line: ln})
            text = [revisions]
    }
    else if ((diff.length < 2 && diff[0][0] == 0) && (state== 0 || state == 4)) {
        change = "no change";
    }
    else {
        if (state == 1 || state == 2) {
            change = "cut/copy";
            postWriterText({timestamp: time, text: revisions, revision: diff, state: state, cb: clipboard, line: ln})
            text = [revisions]
            clipboard = "";
        }
        else if(diff[0][0] === 1 && state == 4) {
            change = "addition";
            changemade = difference(writerText, revisions)
            postWriterText({timestamp: time, text: revisions, revision: changemade, state: state, cb: clipboard, line: ln})
            text = [revisions]
        }
        else if(diff[1][0] === -1) {
            change = "deletion";

            if ((diff[1][1].includes('\n') || diff[1][1].includes(' '))|| state != 0 || diff.length > 3){
               // if user delete a space, the chars array will be send to the backend for processing
                changemade = difference(text[0], revisions)
                postWriterText({timestamp: time, text: revisions, revision: changemade, state: state, line: ln})
                text = [revisions]
            }
        }
        else if (diff[1][0] === 1){
            change = "addition";
            if ((diff[1][1].includes('\n') || diff[1][1].includes(' ')) || state != 0 || diff.length > 3){
                // if user add a space, the chars array will be send to the backend for processing
                changemade = difference(text[0], revisions)
                postWriterText({timestamp: time, text: revisions, revision: changemade, state: state, line: ln})
                text = [revisions]
            }
        }
    }
}

async function fetchFromServer(route, activity){
    const response = await fetch(serverURL + route, {
        // mode: 'no-cors',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        method: 'POST',
        body: JSON.stringify(activity),
    });
    const message = await response.json();
    return message;
}

async function postWriterText(activity) {
    activity["username"] = username;
    activity["project"] = projectID;
    activity["onkey"] = onkey;
    activity["file"] = filename;
    activity["editingLines"] = editingLines;
    activity["message"] = action;
    console.log("postWriterText",activity);
    try {
        var message = await fetchFromServer("/activity", activity);
        console.log(message);
    }
    catch (err){
        console.log(err);
        console.log('failed to fetch');
    }
}

async function postParaphraseText(activity, tabId) {
    activity["username"] = username;
    console.log("postParaphraseText",activity);
    try {
        var message = await fetchFromServer("/paraphrase", activity);
        console.log(message);
        if (message.status == "ChatGPT"){
            chrome.tabs.sendMessage(tabId, {source: "chatgpt", suggestion: message.suggestion,
                    same_line_before: message.same_line_before, same_line_after: message.same_line_after,
                    diffs_html: message.diffs_html, explanation: message.explanation, line: message.line},
            function (response) {
            });
        }
    }
    catch (err){
        console.log(err);
        console.log('failed to fetch');
    }
}