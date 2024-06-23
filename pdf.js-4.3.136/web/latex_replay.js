let isPlaying = false
let previousFrame
let stopOrPlay
let nextFrame
let slider
let frameNumberInput
let replaySpeed
let intervalId
let baseIntervalTime = 1000
let currentIntervalTime = baseIntervalTime

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
}

function getFrameNumber(){
    return parseInt(slider.value)
}

function play(){
    intervalId = setInterval(addFrameNumber, currentIntervalTime)
}

function pause(){
    clearInterval(intervalId)
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

window.addEventListener('load', function() {
    previousFrame = this.document.getElementById("previousFrame");
    pauseOrPlay = this.document.getElementById("pauseOrPlay");
    nextFrame = this.document.getElementById("nextFrame");

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

})
