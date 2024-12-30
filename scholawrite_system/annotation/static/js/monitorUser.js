let arrayIdx = 0
let metaBox;
let lineBox;
let contentBox;
let currentTex = 0;
let currentIndex = 0
let indexObj = {}
let isCurrentModeByFiles = false;
let mainLoader

let fileBox
let timeStampBox
let userNameBox

console.log(actions_obj)
console.log(revisions_obj)

let organizedData = {};

let maxObj = {}
let minObj = {}

// section of variable that used for file annotation
let currentGlobalIdx;
let filesLabelArray = {};
let filledArray;
let currentLabelArray;

// Legacy version
// let valueToLabel = {
//     1: "Idea Generation", 2: "Idea Organization", 3: "Discourse Planning",
//     4: "Drafting", 5: "Lexical Chaining", 6: "Object Insertion",
//     7: "Semantic", 8: "Syntactic", 9: "Lexical",
//     10: "Structural", 11: "Visual", 12: "Quantitative",
//     13: "Feedback", 0: "No Label", 14: "Artifact", 15:"Command Insertion",
//     16: "Citation"
// }


let fetchIdx;

function generateIndexObj(data) {
  const fileNamesSet = filenames_obj;
  const fileNameObj = {}

  for (const value of fileNamesSet) {
    if (!fileNameObj[value])
    {
        fileNameObj[value] = 0
    }
}

  // Convert the Set to an array and return it
  return fileNameObj
}

// helper function call by load_frame that fetch edits from server
async function get_frame(){
    try{
        const response = await fetch("/api/monitoruser", {
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            method: 'POST',
            body: JSON.stringify({idx: fetchIdx, file: currentTex}),
        });
        const message = await response.json();
        return message;
    } catch (error){
        alert("Fail to load your progress!\n Please contact developer.")
    }
}

async function load_frame(){
    // If the idx exceed the range of given data, fetch from the server.
    if ((indexObj[currentTex] > maxObj[currentTex]) || (indexObj[currentTex] < minObj[currentTex])){
        console.log("fetch!")
        fetchIdx = indexObj[currentTex];
        pyDict = await get_frame();
        organizeByTex(pyDict["revisions"], pyDict["actions"]);
        arrayIdx = pyDict["arrayIdx"];
        minObj[currentTex] = indexObj[currentTex] - arrayIdx;
        maxObj[currentTex] = minObj[currentTex] + revisions_obj.length - 1;
    }

    // render the frame along with metadata
    // show filename, username, timestamp, index, and lable of current frame
    arrayIdx = indexObj[currentTex] - minObj[currentTex]

    fetchIdx = indexObj[currentTex];
    console.log("fetchIdx: ", fetchIdx);

    metaBox.innerHTML = organizedData[currentTex][arrayIdx]["file"]+'<br>'+
        organizedData[currentTex][arrayIdx]["username"]+"<br>"+
        organizedData[currentTex][arrayIdx]["timestamp"]+"<br>"+indexObj[currentTex]+ "<br>"
        + JSON.stringify(filesLabelArray[currentTex][indexObj[currentTex]]);

    // redner the frame and line numbers
    userNameBox = organizedData[currentTex][arrayIdx]["username"]
    contentBox.innerHTML = organizedData[currentTex][arrayIdx]["diff_html"]
    let lineNums = organizedData[currentTex][arrayIdx]["line_nums"]
    let line_text = ""
    for (var i=0; i< lineNums.length; i++){
        line_text = line_text + lineNums[i] + "<br>";
    }
    lineBox.innerHTML = line_text;
}

function generateButtons(fileNamesArray) {
  const btnGroup = document.querySelector('.fileButtons');

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

    if (index === 0) {
      radioInput.checked = true;
      currentTex = label.textContent
    }

    // Append radio input and label to the button group
    btnGroup.appendChild(radioInput);
    btnGroup.appendChild(label);

    label.onclick = function() {
      // Call a custom function when the button is clicked
      handleTabClick(index, label.textContent);
    };
  });

  // Add the flex div
  const flexDiv = document.createElement('div');
  flexDiv.style.flex = '1';
  btnGroup.appendChild(flexDiv);
}

function handleTabClick(index, fileName) {
    // Add your logic here when a button is clicked
    console.log(index)
    currentIndex = index
    currentTex = fileName
    // re-sets the value of the slider to appropriate index
    // Get the slider element
    var slider = document.getElementById('myRange');
    // Set the new value
    console.log(indexObj)
    // Set the new max value
    slider.setAttribute('data-slider-max', no_of_doc_file[currentTex] - 1);

    // adds max length to the slider
    let fileLength = no_of_doc_file[currentTex] - 1
    let fileSizeDoc = document.getElementById('fileSize');
    fileSizeDoc.innerHTML = fileLength;

    slider.max = no_of_doc_file[currentTex] - 1;

    var inputEvent = new Event('input', { bubbles: true });
    slider.value = indexObj[fileName];

    // for file level annotation
    currentGlobalIdx = global_indexes[currentTex]
    currentLabelArray = filesLabelArray[currentTex]

    let composition = calculatePercentage(currentLabelArray);
    drawProgressBar(composition);

    load_frame()
}

function organizeByTex(data, fileData) {
  let result = {};

  // Iterate through the data and organize by key
  data.forEach((obj, index) => {
    const fileName = fileData[index].file
    const timestamp = fileData[index].timestamp;
    const username = fileData[index].username;

    // Add timestamp to diff_html and line_nums
    obj.timestamp = timestamp;
    obj.username = username;
    obj.file = fileName;

    if (!result[username]) {
      result[username] = [];
    }
    result[username].push(obj);
  });

  for (const key in result) {
    organizedData[key] = result[key];
  }
}

window.addEventListener('load', async function() {
    // Setup the important data that generate frames
    organizeByTex(revisions_obj, actions_obj);

    // minObj and maxObj stands for each file's frame interval
    for (const elem of filenames_obj) {
        if (organizedData.hasOwnProperty(elem)){
            minObj[elem] = 0;
            maxObj[elem] = organizedData[elem].length - 1;
        }else{
            minObj[elem] = 0;
            maxObj[elem] = -1;
        }
    }
    console.log("Organized: ", organizedData);
    console.log("minObj: ", minObj);
    console.log("maxObj: ", maxObj);
    console.log("numbers: ", no_of_doc_file)
    indexObj = generateIndexObj(actions_obj)

    // Get elements from HTML document
    metaBox = document.querySelector('#meta');
    lineBox = document.querySelector('#displayLines');
    contentBox = document.querySelector('#displayContent');

    // adds max length to the bottom of the slider
    let firstFile = Object.keys(no_of_doc_file)[0]
    let fileLength = no_of_doc_file[firstFile] - 1
    let fileSizeDoc = document.getElementById('fileSize');
    fileSizeDoc.innerHTML = fileLength;

    // Get the range slider element
    let slider = document.getElementById("myRange");

    // Get the output element where the value will be displayed
    let output = document.getElementById("sliderValue");

    // generates names of the .tex
    indexArr = Array(filenames_obj.length).fill(0)
    generateButtons(filenames_obj);

    // Create an array of zeros for each file based on each length
    for (let key in no_of_doc_file) {
        filesLabelArray[key] = Array(no_of_doc_file[key]).fill(["No Label"]);
    }

    // Set the global index for current on-focus file
    currentGlobalIdx = global_indexes[currentTex];
    currentLabelArray = filesLabelArray[currentTex];

    await loadFromServer();

    //separate data by .tex
    document.querySelector('#prev').addEventListener("click", function(){
        indexArr[currentIndex] = indexArr[currentIndex] - 1;

        if (indexObj[currentTex] > 0){
            indexObj[currentTex] = indexObj[currentTex] - 1;
            slider.value= indexObj[currentTex];
        }
        console.log("Current Index: ", indexObj[currentTex])

        load_frame()
    })
    document.querySelector('#prev_nolabel').addEventListener("click", function(){
    console.log("click")
        for(var i = indexObj[currentTex] - 1; i >= 0; i--){
            if (currentLabelArray[i][0] == "No Label"){
                indexObj[currentTex] = i;
                slider.value= indexObj[currentTex];
                break;
            }
        }
        console.log("Current Index: ", indexObj[currentTex])

        load_frame()
    })
    document.querySelector('#next').addEventListener("click", function(){
        indexArr[currentIndex] = indexArr[currentIndex] + 1

        if (indexObj[currentTex] + 1 < no_of_doc_file[currentTex]){
            indexObj[currentTex] = indexObj[currentTex] + 1
            slider.value= indexObj[currentTex]
        }
        console.log("Current Index: ", indexObj[currentTex])

        load_frame()
    })
    document.querySelector('#next_nolabel').addEventListener("click", function(){
        for(var i = indexObj[currentTex] + 1; i < no_of_doc_file[currentTex]; i++){
            if (currentLabelArray[i][0] == "No Label"){
                indexObj[currentTex] = i;
                slider.value= indexObj[currentTex];
                break;
            }
        }
        console.log("Current Index: ", indexObj[currentTex])

        load_frame()
    })
    document.querySelector('#jump').addEventListener("click", function(){
        let jump = document.getElementById("jumpIndex").value;
        jump = parseInt(jump)

        if (jump >= no_of_doc_file[currentTex])
        {
            alert("Please choose a smaller value!")
        }
        else if (jump < 0)
        {
            alert("Please choose a positive value!")
        }
        else{
            indexObj[currentTex] = jump
            slider.value= indexObj[currentTex]
        }
        console.log("Current Index: ", indexObj[currentTex])

        load_frame()
    })

    // set the slider unbound for first displayed file
    slider.setAttribute('data-slider-max', no_of_doc_file[currentTex] - 1);
    slider.max = no_of_doc_file[currentTex] - 1;
    //Render the initial frame once user load the page
    load_frame()

    // Add an onchange event listener to the slider
    slider.oninput = function() {
    onChangeFunction(this.value);
    };

    // Custom onchange function for slider
    function onChangeFunction(value) {
    let setIndex = parseInt(value)

    indexObj[currentTex] = setIndex

    load_frame()
    }

    // detect keyboard press for moving index
    window.addEventListener("keydown", (event) => {
        // right arrow
        if (event.isComposing || event.keyCode === 39) {
            console.log("Right arrow pressed")
            indexObj[currentTex] = indexObj[currentTex] + 1
            slider.value= indexObj[currentTex]
            load_frame()
        }
        else if (event.isComposing || event.keyCode === 37) {
            console.log("Left arrow pressed")
            indexObj[currentTex] = indexObj[currentTex] - 1
            slider.value= indexObj[currentTex]
            load_frame()
        }
    });

    // use Select2 on select element
    let select2Element = $("#swLabels")
    select2Element.select2({
        tags: true
    })


    $("#annotate").on("click", function(){
        let start = $("#startIdx").val() === "" ? undefined : $("#startIdx").val();
        let end = $("#endIdx").val() === "" ? undefined : $("#endIdx").val();
        let label = $('#swLabels').val();
        if (start == "" || end == "" || label.length == 0){
            alert("Please fill out all three fields");
        }else{
            start = Number(start);
            end = Number(end);
            if(!Number.isInteger(start) || !Number.isInteger(end)){
                alert("Ending or starting index should be an integer");
            }else if(end > no_of_doc_file[currentTex] - 1 || end < 0){
                alert("Ending index out of range");
            }else if(start > no_of_doc_file[currentTex] - 1 || start < 0){
                alert("Starting index out of range");
            }else if(start > end){
                alert("Starting index cannot larger than ending index");
            }else if((end - start) >= 200){
                alert("You are annotating over 200 edits\nPlease reduce the interval");
            }else{
                start = parseInt(start)
                end = parseInt(end)
                for(var i = start; i<= end; i++){
                    currentLabelArray[i] = label;
                    filledArray[currentGlobalIdx[i]] = label
                }
                // for showing the annotation progress of one file
                filesLabelArray[currentTex] = currentLabelArray;
                let composition = calculatePercentage(currentLabelArray);
                drawProgressBar(composition);

                // for storing the annotation progress of whole project
                composition = calculatePercentage(filledArray);
                saveToServer({filledArray: filledArray, composition: composition})

                // reset value from input box
                $("#startIdx").val(end+1);
                $("#endIdx").val("");
                $("#swLabels").val(null).trigger("change");

                // sets the current index to the index right after the previous end index
                if (end + 1 < no_of_doc_file[currentTex]){
                    indexObj[currentTex] = end + 1;
                    slider.value= indexObj[currentTex];
                    load_frame();
                }else{
                    indexObj[currentTex] = end;
                    slider.value= indexObj[currentTex];
                    load_frame();
                }
            }
        }
    });

    $("#switchFile").on("click", function() {
        var selectedOption = $("#title").val();
        window.location.href = "/monitoruser?project_id="+selectedOption;
    });

    $("#download").on("click", downloadFile);
})

// function that runs before load
window.onbeforeunload = function () {
    console.log("Loading Monitor")
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
            for (let tex in global_indexes){
                tempGlobalIdx = global_indexes[tex];
                templateArray = []
                for (var i = 0; i<tempGlobalIdx.length; i++){
                    templateArray.push(filledArray[tempGlobalIdx[i]]);
                }
                filesLabelArray[tex] = templateArray;
            }
            currentLabelArray = filesLabelArray[currentTex];
            let composition = calculatePercentage(currentLabelArray);
            drawProgressBar(composition);
        }else{
            // initialize the array of global label
            filledArray = new Array(no_of_doc).fill(["No Label"]);
        }
    } catch (error) {
        alert("Fail to load your progress!\n Please contact developer.")
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
    const labels = prepareFileData(filledArray)
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