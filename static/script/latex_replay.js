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


let contentBox;
let lineBox;

let labelbox;

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

    renderFrame(getFrameNumber());
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



function renderFrame(arrayIdx){

    // render the frame and line numbers
    llama3ContentBox.innerHTML = llama3Revisions[arrayIdx]["revision"]
    llama8ContentBox.innerHTML = llama8Revisions[arrayIdx]["revision"]

    llama3Label.innerHTML = llama3Labels[arrayIdx]["label"]
    llama8Label.innerHTML = llama8Labels[arrayIdx]["label"]
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

    window.addEventListener('keydown', event => {
        if (event.key == "ArrowLeft") {
            minusFrameNumber()
        } else if (event.key == "ArrowRight") {
            addFrameNumber()
        }
    })

    slider = this.document.getElementById("latexFrameSlider");
    frameNumberInput = this.document.getElementById("latexFrameNumberInput")
    verticalLine = document.getElementById('verticalLine');

    llama3Label= document.getElementById('llama3Label');
    llama8Label= document.getElementById('llama8Label');

    slider.addEventListener("change", function(){
        setFrameNumber(slider.value);
    })

    frameNumberInput.addEventListener("change", function(){
        setFrameNumber(frameNumberInput.value);
    })

    llama3ContentBox = this.document.getElementById("llama3DisplayContent");
    llama8ContentBox = this.document.getElementById("llama8DisplayContent");

    renderFrame(0)
})


function changeSeed(event){
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target).entries());
    window.location.replace(window.location.origin + '/scholawrite/model_outputs/'+data.seed_doc+".html")
}
