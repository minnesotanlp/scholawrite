import { AppOptions } from "./app_options.js";
import { PDFViewerApplication } from "./app.js";
import {getViewerConfiguration} from "./viewer.js"

let isPlaying = false
let previousFrame
let pauseOrPlay
let nextFrame
let slider
let frameNumberInput
let replaySpeed
let intervalId
let baseIntervalTime = 1000
let currentIntervalTime = baseIntervalTime

let frameLabel;
let frameFilename;

let contentBox;
let lineBox;

let globalMax = -1;
let globalMin = -1;
let pyDict
let revisions_obj;
let actions_obj;
let latexFrameNumber;


function addFrameNumber(){
    setFrameNumber(getFrameNumber()+ 1)
}

function minusFrameNumber(){
    setFrameNumber(getFrameNumber() - 1)
}

function setFrameNumber(value){
    let min = parseInt(slider.getAttribute("min"))
    let max = parseInt(slider.getAttribute("max"))

    if (min <= value && value <= max){
        slider.value = value
        frameNumberInput.value = value
    }

    load_frame(getFrameNumber());
}

function getFrameNumber(){
    return parseInt(slider.value)
}

function play(){
    intervalId = setInterval(addFrameNumber, currentIntervalTime)
}

function pause(){
    clearInterval(intervalId);
    intervalId = null;
}

function setReplaySpeed(factor){
    currentIntervalTime = baseIntervalTime / factor
    if (pauseOrPlay.getAttribute("data-state") == "play"){
        pause();
        play();
    }
}

function mediaControl(event){
    if (event.target.getAttribute("data-state") == "play"){
        $(event.target).replaceWith(`<i id="pauseOrPlay" class="fa-solid fa-play latexPlayButton" data-state="pause"></i>`);
        pause();
    }else{
        $(event.target).replaceWith(`<i id="pauseOrPlay" class="fa-solid fa-pause latexPlayButton" data-state="play"></i>`);
        play();
    }
    pauseOrPlay = document.getElementById("pauseOrPlay");
    pauseOrPlay.addEventListener("click", mediaControl);
}


// load the frame based on idx
async function load_frame(idx){
    // If the idx exceed the range of given data, fetch from the server.
    let arrayIdx;

    if((idx > globalMax) || (idx < globalMin)){
        pauseOrPlay.setAttribute("data-state", "play")
        pauseOrPlay.click();

        let fetchIdx = idx;
        console.log("fetch!")
        pyDict = await fetchDataFromServer("/api/monitor", {idx: fetchIdx, file: frameFilename.innerText, paperUrl: AppOptions.get("defaultUrl")});
        actions_obj = pyDict["actions"];
        revisions_obj = pyDict["revisions"];
        arrayIdx = pyDict["arrayIdx"];
        globalMin = idx - arrayIdx;
        globalMax = globalMin + revisions_obj.length - 1; // -1 to make sure align with the array index
        
        arrayIdx = idx - globalMin;
        renderFrame(revisions_obj, actions_obj, arrayIdx);

        pauseOrPlay.setAttribute("data-state", "pause")
        pauseOrPlay.click();
    }

    arrayIdx = idx - globalMin;
    renderFrame(revisions_obj, actions_obj, arrayIdx);

}


function renderMetadata(dataFromServer){
    frameFilename.innerText = dataFromServer["file"]
    latexFrameNumber.innerText = dataFromServer["no_of_doc"]
    frameNumberInput.max = dataFromServer["no_of_doc"]
    slider.max = dataFromServer["no_of_doc"]

}


function renderFrame(revisions_obj, actions_obj, arrayIdx){

    // set the label of current frame
    frameLabel.innerText = actions_obj[arrayIdx]["label"]

    // render the frame and line numbers
    contentBox.innerHTML = revisions_obj[arrayIdx]["diff_html"]
    let lineNums = revisions_obj[arrayIdx]["line_nums"]
    let line_text = ""
    for (var i=0; i< lineNums.length; i++){
        line_text = line_text + lineNums[i] + "<br>";
    }
    lineBox.innerHTML = line_text;
}


async function lookupFileFromServer(pageNumer, left, top){
    console.log(pageNumer, left, top)

    let dataFromServer = await fetchDataFromServer("/api/section",{pageNumer: pageNumer, left: left, top:top, paperUrl: AppOptions.get("defaultUrl")})

    if (dataFromServer["file"] != frameFilename.innerText){
        renderMetadata(dataFromServer)
        slider.value = 0
        frameNumberInput.value = 0
        globalMin = -1
        globalMax = -1
        load_frame(0)
    }
}

/* Dynamically add event listner to pdf text lines 
   as these elements will collapse and expand when user scroll.*/
$("#mainContainer").on("pointermove mousemove mousewheel ", function(){
        $('[role="presentation"]').off('dblclick')

        $('[role="presentation"]').dblclick(function() {
            let pageNumer = $(this).parent().parent().data("page-number")
            let left = (parseFloat(this.style.left) / 100) *595
            let top = (parseFloat(this.style.top) / 100) * 842

            lookupFileFromServer(pageNumer, left, top)
        });
})

function setProjectPdfUrl(project_name){
    AppOptions.set("defaultUrl", "projects/"+project_name)
}

function displayProjectPdf(){
    let config = getViewerConfiguration()
    PDFViewerApplication.run(config)
}

window.addEventListener('DOMContentLoaded', function() {
    previousFrame = document.getElementById("previousFrame");
    pauseOrPlay = document.getElementById("pauseOrPlay");
    nextFrame = document.getElementById("nextFrame");

    pauseOrPlay.addEventListener("click", mediaControl);

    previousFrame.addEventListener("click", function(){
        minusFrameNumber()
    })

    nextFrame.addEventListener("click", function(){
        addFrameNumber()
    })


    slider = this.document.getElementById("latexFrameSlider");
    frameNumberInput = this.document.getElementById("latexFrameNumberInput")

    slider.addEventListener("change", function(){
        setFrameNumber(slider.value);
    })

    frameNumberInput.addEventListener("change", function(){
        setFrameNumber(frameNumberInput.value);
    })


    replaySpeed = this.document.getElementById("replaySpeed");

    replaySpeed.addEventListener("change", function(){
        setReplaySpeed(this.value)
    })

    let latexProjectSelector = this.document.getElementById("latexProjectSelector")

    latexProjectSelector.addEventListener("change", function(){
        setProjectPdfUrl(this.value)
        displayProjectPdf()
    })

    frameLabel = $("#latexFrameLabel :nth-child(2)")[0];
    frameFilename = $("#latexFilename :nth-child(2)")[0];
    latexFrameNumber = $("#latexFrameNumber :nth-child(2)")[0];

    lineBox = this.document.getElementById("displayLines");
    contentBox = this.document.getElementById("displayContent");
})


async function fetchDataFromServer(path, object){
    try {
        const response = await fetch(path, {
            method: "POST",
            body: JSON.stringify(object),
            headers: {
                "Content-type": "application/json;"
            }
        });

        // Check if the response status is not 200
        if (response.status !== 200) {
            alert("Fail to get data from server!\n Please contact developer.");
            return null;
        }

        const dataFromServer = await response.json();
        return dataFromServer;
    } catch (error) {
        // Handling network errors or other fetch related errors
        alert("Fail to get data from server!\n Please contact developer.");
        return null;
    }
}