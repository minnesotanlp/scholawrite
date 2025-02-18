let idx = 0;
let arrayIdx = 0;
let globalMin = 0;
let globalMax = -1;
let metaBox;
let lineBox;
let contentBox;
let loadBox;
let buttonGroupBox
let mainBox
let mainLoader
let organizedData = {};
console.log(actions_obj)
console.log(actions_obj[0])
let isLoading = false;

let filledArray;

// legacy version
// let valueToLabel = {
//     1: "Idea Generation", 2: "Idea Organization", 3: "Discourse Planning",
//     4: "Drafting", 5: "Lexical Chaining", 6: "Object Insertion",
//     7: "Semantic", 8: "Syntactic", 9: "Lexical",
//     10: "Structural", 11: "Visual", 12: "Quantitative",
//     13: "Feedback", 0: "No Label", 14: "Artifact", 15:"Command Insertion",
//     16: "Citation"
// }

let fetchIdx;

// helper function call by load_frame that fetch edits from server
async function get_frame(){
    try{
        const response = await fetch("/api/monitorwhole", {
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            method: 'POST',
            body: JSON.stringify({idx: fetchIdx}),
        });
        const message = await response.json();
        return message;
    } catch (error){
        alert("Fail to load your progress!\n Please contact developer.")
    }
}

// load the frame based on idx
async function load_frame(){
    // If the idx exceed the range of given data, fetch from the server.
    if((idx > globalMax) || (idx < globalMin)){
        // displays the loader
        loadBox.style.display = ""
        // hides button group
        //buttonGroupBox.style.display = "none"
        mainBox.style.display = "none"

        fetchIdx = idx;
        console.log("fetch!")
        pyDict = await get_frame();
        actions_obj = pyDict["actions"];
        revisions_obj = pyDict["revisions"];
        arrayIdx = pyDict["arrayIdx"];
        globalMin = idx - arrayIdx;
        globalMax = globalMin + revisions_obj.length - 1; // -1 to make sure align with the array index
    }
    
    // render the frame along with metadata
    // show filename, username, timestamp, index, and lable of current frame
    arrayIdx = idx - globalMin
    metaBox.innerHTML = actions_obj[arrayIdx]["file"]+'<br>'+actions_obj[arrayIdx]["username"]
    +"<br>"+actions_obj[arrayIdx]["timestamp"]+"<br>"+idx + "<br>"
    + JSON.stringify(filledArray[idx]);

    // render the frame and line numbers
    contentBox.innerHTML = revisions_obj[arrayIdx]["diff_html"]
    let lineNums = revisions_obj[arrayIdx]["line_nums"]
    let line_text = ""
    for (var i=0; i< lineNums.length; i++){
        line_text = line_text + lineNums[i] + "<br>";
    }
    lineBox.innerHTML = line_text;


    // hides the loader
    loadBox.style.display = "none"
    // shows the button group
    // buttonGroupBox.style.display = ""
    mainBox.style.display = ""
}

function getFileNames(data) {
  const fileNamesSet = new Set();

  // Iterate through the original data and add unique file names to the Set
  data.forEach(item => {
    fileNamesSet.add(item.file);
  });

  // Convert the Set to an array and return it
  return Array.from(fileNamesSet);
}

function generateButtons(fileNamesArray) {
  const btnGroup = document.querySelector('.fileButtons');

  // Clear existing buttons
  while (btnGroup.firstChild) {
    btnGroup.removeChild(btnGroup.firstChild);
  }

  // Create and append buttons based on the file names array
  fileNamesArray.forEach((fileName, index) => {
    const radioId = `btnradio${index + 1}`;

    // Create radio input
    const radioInput = document.createElement('input');
    radioInput.type = 'radio';
    radioInput.className = 'btn-check';
    radioInput.name = 'btnradio';
    radioInput.id = radioId;
    radioInput.autocomplete = 'off';

    // Create label
    const label = document.createElement('label');
    label.className = 'btn btn-outline-primary rounded';
    label.setAttribute('for', radioId);
    label.textContent = `${fileName}`;

    // Check the radio button based on the condition
    if (actions_obj[arrayIdx]["file"] == fileName) {
      radioInput.checked = true;
    }

    // Add a click event listener to prevent default behavior
    radioInput.addEventListener('click', function(event) {
      event.preventDefault();
    });

    // Append radio input and label to the button group
    btnGroup.appendChild(radioInput);
    btnGroup.appendChild(label);
  });

  // Add the flex div
  const flexDiv = document.createElement('div');
  flexDiv.style.flex = '1';
  btnGroup.appendChild(flexDiv);
}

window.addEventListener('load', async function() {
    metaBox = document.querySelector('#meta');
    lineBox = document.querySelector('#displayLines');
    contentBox = document.querySelector('#displayContent');
    let slider = document.getElementById("myRange");
    buttonGroupBox = document.getElementById("buttonGroup");
    mainBox = document.getElementById("mainContainer");
    loadBox =document.getElementById("loader");

    globalMax = actions_obj.length - 1;

    // Get the output element where the value will be displayed
    let output = document.getElementById("sliderValue");

    // generates names of the .tex
    const fileNamesArray = filenames_obj;
    console.log(fileNamesArray)
    generateButtons(fileNamesArray);

    document.querySelector('#prev').addEventListener("click", function(){
        if (idx > 0)
        {
            idx = idx - 1;
            slider.value = idx;
            load_frame().then(function() {
                generateButtons(fileNamesArray);
            })
        }
    })
    document.querySelector('#prev_nolabel').addEventListener("click", function(){
        for (var i = idx - 1; i >= 0; i--){
            if (filledArray[i][0] != "No Label"){
                continue
            }else{
                idx = i;
                slider.value = idx;
                load_frame().then(function() {
                    generateButtons(fileNamesArray);
                });
                break
            }
        }
    })
    document.querySelector('#next').addEventListener("click", function(){
        if (idx < no_of_doc - 1)
        {
            idx = idx + 1;
            slider.value = idx;
            load_frame().then(function() {
                generateButtons(fileNamesArray);
            });
        }
    })
    document.querySelector('#next_nolabel').addEventListener("click", function(){
        for(var i = idx + 1; i < no_of_doc; i++){
            if (filledArray[i][0] != "No Label"){
                continue
            }else{
                idx = i;
                slider.value = idx;
                load_frame().then(function() {
                    generateButtons(fileNamesArray);
                });
                break
            }
        }
    })
    document.querySelector('#jump').addEventListener("click", function(){
        let jump = document.getElementById("jumpIndex").value;
        jump = parseInt(jump)

        if (jump > no_of_doc - 1)
        {
            alert("Please choose a smaller value!")
        }
        else if (jump < 0)
        {
            alert("Please choose a positive value!")
        }
        else{
            idx = jump
            slider.value= idx
            generateButtons(fileNamesArray);
        }
        load_frame()
    })

    await loadFromServer();
    //load the first frame after page load
    load_frame()

    // slider
    slider.oninput = function() {
    onChangeFunction(this.value);
    };

    // Custom onchange function for slider
    function onChangeFunction(value) {
        let setIndex = parseInt(value)
        idx = setIndex
        console.log(idx)
        // load the frame and generate a new button group
        load_frame().then(function() {
            generateButtons(fileNamesArray);
        })
    }

    // detect keyboard press for moving index
    window.addEventListener("keydown", (event) => {
        if (document.activeElement.tagName !== "INPUT" && event.key === "ArrowRight") {
            console.log("Right arrow pressed")
            if(idx < no_of_doc - 1){
                idx = idx + 1
                slider.value= idx
                load_frame().then(function() {
                    generateButtons(fileNamesArray);
                })
            }
        }
        else if (document.activeElement.tagName !== "INPUT" && event.key === "ArrowLeft") {
            console.log("Left arrow pressed")
            if (idx > 0){
                idx = idx - 1
                slider.value= idx
                load_frame().then(function() {
                    generateButtons(fileNamesArray);
                })
            }
        }
    });

    // use Select2 on select element
    let select2Element = $("#swLabels")
    select2Element.select2({
        tags: true
    })

    $("#annotate").on("click", function(){
        let start = $("#startIdx").val();
        let end = $("#endIdx").val();
        let label = $('#swLabels').val();
        if (start == "" || end == "" || label.length == 0){
            alert("Please fill out all three fields");
        }else{
            start = Number(start);
            end = Number(end);
            if(!Number.isInteger(start) || !Number.isInteger(end)){
                alert("Ending or starting index should be an integer");
            }else if(end > no_of_doc - 1 || end < 0){
                alert("Ending index out of range");
            }else if(start > no_of_doc - 1 || start < 0){
                alert("Starting index out of range");
            }else if(start > end){
                alert("Starting index cannot larger than ending index");
            }else if((end - start) >= 200){
                alert("You are annotating over 200 edits\nPlease reduce the interval");
            }else{
                for(var i = start; i<= end; i++){
                    filledArray[i] = label
                }
                let composition = calculatePercentage(filledArray);
                drawProgressBar(composition);
                saveToServer({filledArray: filledArray, composition: composition})
                // sets the start index to the index right after the previous end index
                $("#startIdx").val(end+1);
                $("#endIdx").val("");
                $("#swLabels").val(null).trigger("change");
                // sets the current index to the index right after the previous end index
                if (end + 1 < no_of_doc){
                    idx = end + 1
                    slider.value = idx;
                    load_frame().then(function() {
                        generateButtons(fileNamesArray);
                    })
                } else{
                    idx = end
                    slider.value = idx;
                    load_frame().then(function() {
                        generateButtons(fileNamesArray);
                    })
                }
            }
        }
    });

    $("#switchFile").on("click", function() {
        var selectedOption = $("#title").val();
        window.location.href = "/monitorwhole?project_id="+selectedOption;
    });

    $("#download").on("click", downloadFile);
})

// function that runs before load
window.onbeforeunload = function () {
    console.log("Loading Monitor Whole")
    let body = document.getElementById("body");

    // hides body while loading
    body.style.display = "none"

    // shows the main loader while loading
    mainLoader = document.getElementById("mainLoader");
    mainLoader.style.display = "block";
}


// Calculate the percentage of each section in the array.
// if next element does not equal to current element, we calculate the percentage.
// e.g. input: [1, 1, 1, 2, 2, 2, 1, 3, 3, 3]
// output: [[1, "30.00%"], [2, "30.00%"], [1, "10.00%"], [3, "30.00%"]]
//function calculatePercentage(array) {
//    const counts = [];
//    const totalCount = array.length;
//		var lastidx = 0;
//		for (var i = 0; i< array.length - 1; i++){
//            if (array[i] != array[i+1]){
//            const percentage = ((i - lastidx + 1) / array.length) * 100;
//            counts.push([array[i], percentage.toFixed(2) + "%"])
//            lastidx = i + 1
//      }
//    }
//
//    const percentage = ((i - lastidx + 1) / array.length) * 100;
//    counts.push([array[i], percentage.toFixed(2) + "%"])
//    lastidx = i + 1
//
//    return counts;
//}

function calculatePercentage(array) {
    let composition = [];
    let count = 0;
    let percentage;
    let previous_label;

    if (array[0].toString() != "No Label"){
        previous_label = "Label"
    }else{
        previous_label = "No Label"
    }

    for (var i = 0; i< array.length; i++){
        label = array[i].toString()
        if (label != "No Label"){
            label = "Label"
        }

        if (label == previous_label){
            count = count + 1
        }
        else {
            percentage = (count / array.length) * 100;

            if(previous_label != "No Label"){
                composition.push([3, percentage]);
            }else{
                composition.push([0, percentage]);
            }

            previous_label = label
            count = 1;
        }
    }

    percentage = (count / array.length) * 100;

    if(previous_label != "No Label"){
        composition.push([3, percentage]);
    }else{
        composition.push([0, percentage]);
    }

    return composition;
}

function drawProgressBar(composition){
    $(".progress-stacked").empty();
    for (var i = 0; i < composition.length; i++){
        if (composition[i][0] == 3){
            // Showing labeled stack on the progress bar
            var bar = `<div class="progress" role="progressbar" style="width: `+ composition[i][1] +`%">
            <div class="progress-bar progress-bar-striped labeled"></div></div>`;
            $(".progress-stacked").append(bar);
        }else{
            // Showing unlabeled stack on the progress bar
            var bar = `<div class="progress" role="progressbar" style="width: `+ composition[i][1] +`%">
            <div class="progress-bar progress-bar-striped noLabel"></div></div>`;
            $(".progress-stacked").append(bar);
        }
    }
}

// Calculate the beginning and ending of each label in the array.
// if next label does not equal to current label, we calculate the beginning and ending of current label.
// e.g. input: [1, 1, 1, 2, 2, 2, 1, 3, 3, 3]
// output: [["ideaGeneration", 0, 2], ["ideaOrganization", 3, 5], ["ideaGeneration", 6, 6], ["discoursePlanning", 7, 9]]
function prepareFileData(array) {
    const labels = [];
    const totalCount = array.length;
    var lastidx = 0;

    for (var i = 0; i< array.length - 1; i++){
        if (array[i].toString() != array[i+1].toString()){
            let temp = [...array[i]];
            temp.push(lastidx, i);
            labels.push(temp);
            lastidx = i + 1
        }
    }

    let temp = [...array[i]];
    temp.push(lastidx, i);
    labels.push(temp);
    lastidx = i + 1

    return labels;
}

function downloadFile(){
    let labels = prepareFileData(filledArray)
    let data = {annotator: annotatorEmail, projectId: projectId, labels: labels}
    const jsonData = JSON.stringify(data);
    const blob = new Blob([jsonData], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;

    function get_filename() {
        const date = new Date();

        let month = date.getMonth() + 1;
        let day = date.getDate();
        let year = date.getFullYear();
        let hours = date.getHours();
        let minutes = date.getMinutes();


        month = month < 10 ? '0' + month : month;
        day = day < 10 ? '0' + day : day;
        year = year.toString().substr(-2);
        hours = hours < 10 ? '0' + hours : hours;
        minutes = minutes < 10 ? '0' + minutes : minutes;

        return `${month}_${day}_${year}-${hours}_${minutes}-${annotatorEmail}`;
    }

    a.download = get_filename() + ".json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function saveToServer(object){
    fetch("/api/save", {
        method: "POST",
        body: JSON.stringify(object),
        headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then((response) => {
        if (response.status != 200){
            alert("Fail to save your progress!\n Please contact developer.")
        }
    }).catch((error) => {
        alert("Fail to save your progress!\n Please contact developer.")
    });
}

async function loadFromServer(object){
    try{
        const response = await fetch("/api/load", {
            method: "GET",
            headers: {
                "Content-type": "application/json; charset=UTF-8"
            }
        })
        if (response.status != 200){
            alert("Fail to load your progress!\n Please contact developer.")
        }
        const json = await response.json();
        console.log(json);
        if ("filledArray" in json){
            filledArray = json.filledArray;
            let composition = calculatePercentage(filledArray);
            drawProgressBar(composition)
        }else{
            filledArray = new Array(no_of_doc).fill(["No Label"]);
        }
    } catch (error) {
        alert("Fail to load your progress!\n Please contact developer.")
    }
}