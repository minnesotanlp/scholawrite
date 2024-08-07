import { AppOptions } from "./app_options.js";
import { PDFViewerApplication } from "./app.js";
import {getViewerConfiguration} from "./viewer.js"
import { PDFPageView } from "./pdf_page_view.js";

let isPlaying = false
let previousFrame
let pauseOrPlay
let nextFrame
let slider
let verticalLine
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

let pdfMap = {}

let labelClass = {"Idea Generation" : "planning", "Idea Organization": "planning", "Section Planning":"planning",
                "Text Production" : "implement", "Object Insertion" : "implement", "Citation Integration":"implement",
                "Cross-reference": "implement", "Macro Insertion": "implement", "Fluency" : "revision", 
                "Coherence" : "revision", "Clarity": "revision", "Scientific Accuracy": "revision", 
                "Structural": "revision", "Textual Style": "revision", "Visual Style": "revision"}


let labelColors = {"Idea Generation" : "rgb(86,235,211)", "Idea Organization": "rgb(166,0,62)", "Section Planning":"rgb(100,224,88)",
                "Text Production" : "rgb(135,17,172)", "Object Insertion" : "rgb(69,149,33)", "Citation Integration":"rgb(121,193,239)",
                "Cross-reference": "rgb(14,80,62)", "Macro Insertion": "rgb(189,226,103)", "Fluency" : "rgb(100,66,139)", 
                "Coherence" : "rgb(239,161,204)", "Clarity": "rgb(22,125,187)", "Scientific Accuracy": "rgb(216,94,225)", 
                "Structural": "rgb(252,209,7)", "Textual Style": "rgb(136,60,16)", "Visual Style": "rgb(254,183,134)"}


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


function drawLabelBar(labels){
    let allProgressBar = $('div[class="progress"]')
    allProgressBar.each(function(){
        this.innerHTML = ""
    })

    let planningBar = $('div[class="progress"][id="planning"]')
    let implementBar = $('div[class="progress"][id="implement"]')
    let revisionBar = $('div[class="progress"][id="revision"]')

    let labelsLength = labels.length;
    let labelCount = 0
    let totalwidth = 0
    labels.push("end")
    for(var i=0; i<labelsLength; i++){
        labelCount = labelCount + 1
        let currentLabel = labels[i]
        if (currentLabel != labels[i+1]){
            let numwidth = (labelCount/labelsLength) * 100;
            if (numwidth < 0.044){
                console.log(numwidth)
            }
            let width = numwidth + "%";
            var default_element = $('<div>', {class:"progress-bar progress-bar-striped"});
            default_element.css("background-color", labelColors[currentLabel])
            default_element.css("width", width)
            
            var transparent_element = $('<div>', {class:"progress-bar progress-bar-striped"});
            transparent_element.css("background-color", "transparent")
            transparent_element.css("width", width)
    
            if (labelClass[currentLabel] == "planning"){
                $(planningBar).append(default_element)
    
                $(implementBar).append(transparent_element)
                $(revisionBar).append($(transparent_element).clone())
            }
            else if (labelClass[currentLabel] == "implement"){
                $(implementBar).append(default_element)
                
                $(planningBar).append(transparent_element)
                $(revisionBar).append($(transparent_element).clone())
            }
            else if (labelClass[currentLabel] == "revision"){
                $(revisionBar).append(default_element)
            
                $(implementBar).append(transparent_element)
                $(planningBar).append($(transparent_element).clone())
            }
            else{
                $(revisionBar).append(transparent_element)
                $(implementBar).append($(transparent_element).clone())
                $(planningBar).append($(transparent_element).clone())
            }
            labelCount = 0
        }
    }
    console.log(totalwidth)
}

function renderMetadata(metaData){
    slider.value = 0
    frameNumberInput.value = 0
    globalMin = -1
    globalMax = -1

    frameFilename.innerText = metaData.file
    latexFrameNumber.innerText = metaData.no_of_doc
    frameNumberInput.max = metaData.no_of_doc
    slider.max = metaData.no_of_doc

    drawLabelBar(metaData.all_labels)
}


function renderFrame(revisions_obj, actions_obj, arrayIdx){

    // set the label of current frame
    frameLabel.innerText = actions_obj[arrayIdx]["label"]
    $(frameLabel).css("color", labelColors[actions_obj[arrayIdx]["label"]])

    // render the frame and line numbers
    contentBox.innerHTML = revisions_obj[arrayIdx]["diff_html"]
    let lineNums = revisions_obj[arrayIdx]["line_nums"]
    let line_text = ""
    for (var i=0; i< lineNums.length; i++){
        line_text = line_text + lineNums[i] + "<br>";
    }
    lineBox.innerHTML = line_text;
}


function drawBoundingBox(matchArray){
    matchArray.forEach(function(element){
        $(element).addClass("selectedParagraph")
    })

    // Code for drawing bounding box, not in use.
    //
    // let previousElementHeight = $(matchArray[0]).css("top");
    // let lineGroup = []
    // let spanGroup = []
    // matchArray.forEach(function(element, index){
    //     if ($(element).css("top") == previousElementHeight){
    //         spanGroup.push($(element))
    //     }else{
    //         lineGroup.push(spanGroup)
    //         previousElementHeight = $(element).css("top")
    //         spanGroup = [$(element)]
    //     }
    // })
    // lineGroup.push(spanGroup)

    // lineGroup.forEach(function(line, index) {
    //     if (index == 0){
    //         $(line[0]).addClass("firstSpanBeginParagraph")
    //         for (let i = 1; i < line.length; i++) {
    //             $(line[i]).addClass("middleSapnBeginParagraph")
    //         }
    //         $(line[line.length - 1]).addClass("lastSpanBeginParagraph")
    //     }
    //     else if(0 < index < (lineGroup.length - 2)){
    //         $(line[0]).addClass("fristSpanMiddleParagraph")
    //         $(line[line.length - 1]).addClass("lastSpanMiddleParagraph")
    //     }
    //     else{
    //         $(line[0]).addClass("firstSpanEndParagraph")
    //         for (let i = 1; i < line.length; i++) {
    //             $(line[i]).addClass("middleSapnEndParagraph")
    //         }
    //         $(line[line.length - 1]).addClass("lastSpanEndParagraph")
    //     }
    // })
}

function removeBoundingBox(){
    let current_highlight_elements = $(".selectedParagraph")
    current_highlight_elements.removeClass("selectedParagraph")

    // code for removing bounding box, not in use
    // 
    // let current_highlight_elements = $(".beginParagraph, .middleParagraph, endParagraph")
    // current_highlight_elements.removeClass("beginParagraph")
    // current_highlight_elements.removeClass("middleParagraph")
    // current_highlight_elements.removeClass("endParagraph")
}


/* Dynamically add event listner to pdf text lines 
   as these elements will collapse and expand when user scroll.*/
$("#mainContainer").on("pointermove mousemove mousewheel ", function(){
    let pageArray = $('div[class="page"][data-loaded="true"]')

    pageArray.each(function(){

        let textLineArray = $(this).find('span[role="presentation"][dir="ltr"]');

        textLineArray.off('dblclick')

        textLineArray.each(function(index){
            $(this).on('dblclick', async function() {
                removeBoundingBox();
                let output = await map_pdf_to_latex($(this), index);
                drawBoundingBox(output.matchArray);

                // keep temporarily for display section level visualization
                let target_file = output.target_file
                if (target_file != frameFilename.innerText){
                    let serverData = await fetchDataFromServer("/api/section",{filename: target_file, paperUrl: AppOptions.get("defaultUrl")}) 
                    renderMetadata(serverData)
                    load_frame(0)
                }
            });
        })
    })

})

function setProjectPdfUrl(project_name){
    AppOptions.set("defaultUrl", "projects/"+project_name)
}

function displayProjectPdf(){
    let config = getViewerConfiguration()
    PDFViewerApplication.run(config)
}


function updateVerticalLine() {
    const sliderRect = slider.getBoundingClientRect();
    const sliderValue = slider.value;
    const max = slider.max;
    const min = slider.min;

    // Calculate the left position of the slider handle
    const handlePosition = (sliderValue - min) / (max - min) * sliderRect.width + sliderRect.left;

    // Update the left position of the vertical line
    verticalLine.style.left = `${handlePosition}px`;
    verticalLine.style.top = `${sliderRect.top + sliderRect.height}px`;
}


async function map_pdf_to_latex(textLineElement, index){
    // pdfMap: is a js object. It tells the paragraph location of each line of text on the PDF.
    // {page: [[file name, beginning line number, ending line number], ...], ...}
    // {1: [[main.tex, 1, 2], ....], 2: [[method.tex, 3, 4], ...], ...}

    // First get the page number and index of clicked element in the pdf.
    // this allows us to find the coressponding paragraph location after get the pdfMap from server
    let targetPageNumber = textLineElement.parent().parent().data("page-number")

    // matchArray store elements that are from the same paragraph as clicked element
    let matchArray = []

    // if client don't have pdfMap yet, request from the server
    if (Object.keys(pdfMap).length === 0){
        pdfMap = await fetchDataFromServer(
            "/api/mapping",
            {paperUrl: AppOptions.get("defaultUrl")}
        );
    }
    
    // these three variables will store the file name, beginning and ending line number
    // of clicked element belonging paragraph
    let target_file;
    let target_begin;
    let target_end;

    // if the project currently viewing is eligable to generate the pdfMap
    if (pdfMap.isavailable){

        // Make sure all loaded pages have corresponding data on the pdfMap
        let pageArray = $('div[class="page"][data-loaded="true"]')

        for (const page of pageArray){
            let parentElement = page;
            let pageNumber = $(page).data("page-number");
            let textLineArray = $(page).find('span[role="presentation"][dir="ltr"]');
            let textLineArrayLength = textLineArray.length;

            // if some pages do not have corresponding data, request from the server.
            if (!(pageNumber in pdfMap) || (pdfMap[pageNumber].length != textLineArrayLength)){

                let coordinates = [];

                textLineArray.each(function(){
        
                    const rect = this.getBoundingClientRect();
                    const parentRect = parentElement.getBoundingClientRect();
        
                    const relativeX = rect.left - parentRect.left + (rect.width / 2);
                    const relativeY = rect.top - parentRect.top + (rect.height / 2);
        
                    const dpi_relativeX = (relativeX / parentRect.width) * 595;
                    const dpi_relativeY = (relativeY / parentRect.height) * 842;
                    
                    coordinates.push({left: dpi_relativeX, top:dpi_relativeY, pageNumber: pageNumber, paperUrl: AppOptions.get("defaultUrl")});
                });

                pdfMap = await fetchDataFromServer(
                    "/api/paragraph",
                    {paperUrl: AppOptions.get("defaultUrl"), pageNumber: pageNumber, coordinates: coordinates}
                );
                pdfMap["isavailable"] = true
            }
        }

        // After making sure all loaded pages have corresponding data on the pdfMap, 
        // start to find all the text line elements that are from the same paragraph as clicked element
        target_file = pdfMap[targetPageNumber][index]["file"]
        target_begin = pdfMap[targetPageNumber][index]["begin"]
        target_end = pdfMap[targetPageNumber][index]["end"]

        console.log(target_file, target_begin, target_end)

        for (const pageNum in pdfMap){
            for (var i = 0; i<pdfMap[pageNum].length; i++) {
                let loc = pdfMap[pageNum][i]

                if (loc["file"] == target_file && loc["begin"] == target_begin && loc["end"] == target_end){

                    let match_page = $(`div[class="page"][data-loaded="true"][data-page-number="${pageNum}"]`)
                    let match_element = match_page.find('span[role="presentation"][dir="ltr"]')[i]
                    matchArray.push(match_element)
                }
            }
        }
    }
    console.log(matchArray)

    return {target_file: target_file, target_begin: target_begin, target_end: target_end, matchArray: matchArray}
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
    verticalLine = document.getElementById('verticalLine');

    // Initialize the position of vertical line after the page load
    updateVerticalLine();

    slider.addEventListener("change", function(){
        setFrameNumber(slider.value);
    })

    frameNumberInput.addEventListener("change", function(){
        setFrameNumber(frameNumberInput.value);
    })

    slider.addEventListener("input", function(){
        updateVerticalLine();
    })


    replaySpeed = this.document.getElementById("replaySpeed");

    replaySpeed.addEventListener("change", function(){
        setReplaySpeed(this.value)
    })

    let latexProjectSelector = this.document.getElementById("latexProjectSelector")

    latexProjectSelector.addEventListener("change", function(){
        setProjectPdfUrl(this.value);
        displayProjectPdf();
        pdfMap = {};
    })

    frameLabel = $("#latexFrameLabel :nth-child(2)")[0];
    frameFilename = $("#latexFilename :nth-child(2)")[0];
    latexFrameNumber = $("#latexFrameNumber :nth-child(2)")[0];

    lineBox = this.document.getElementById("displayLines");
    contentBox = this.document.getElementById("displayContent");


    // PDFViewerApplication.eventBus.on('textlayerrendered', map_latex_to_pdf)
    
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