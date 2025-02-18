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
 const response = await fetch("/api/monitor", {
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        method: 'POST',
        body: JSON.stringify({idx: indexObj[currentTex], file: currentTex}),
    });
    const message = await response.json();
    return message;
}

async function load_frame(){
    // If the idx exceed the range of given data, fetch from the server.
    if ((indexObj[currentTex] > maxObj[currentTex]) || (indexObj[currentTex] < minObj[currentTex])){
        console.log("fetch!")
        pyDict = await get_frame();
        organizeByTex(pyDict["revisions"], pyDict["actions"]);
        minObj[currentTex] = pyDict["min"];
        maxObj[currentTex] = pyDict["max"]
    }
    // render the frame along with metadata
    arrayIdx = indexObj[currentTex] - minObj[currentTex]
    metaBox.innerHTML = organizedData[currentTex][arrayIdx]["file"]+'<br>'+organizedData[currentTex][arrayIdx]["username"]+"<br>"+organizedData[currentTex][arrayIdx]["timestamp"]+"<br>"+indexObj[currentTex]
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

  load_frame()
  // You can perform actions like updating the content based on the clicked button, etc.
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

    if (!result[fileName]) {
      result[fileName] = [];
    }
    result[fileName].push(obj);
  });

  for (const key in result) {
    organizedData[key] = result[key];
  }
}

window.addEventListener('load', function() {
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

    //separate data by .tex
    document.querySelector('#prev').addEventListener("click", function(){
        indexArr[currentIndex] = indexArr[currentIndex] - 1

        if (indexObj[currentTex] -1 < 0)
        {
            alert("This is the start of current file!")
        }
        else{
            indexObj[currentTex] = indexObj[currentTex] - 1
            slider.value= indexObj[currentTex]
        }
        console.log("Current Index: ", indexObj[currentTex])

        load_frame()
    })
    document.querySelector('#next').addEventListener("click", function(){
        indexArr[currentIndex] = indexArr[currentIndex] + 1


        if (indexObj[currentTex] + 1 >= organizedData[currentTex].length)
        {
            alert("This is the end of current file!")
        }
        else{
            indexObj[currentTex] = indexObj[currentTex] + 1
            slider.value= indexObj[currentTex]
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
})

// function that runs before load
window.onbeforeunload = function () {
    console.log("Unloading Loader")
    let body = document.getElementById("body");

    // hides body while loading
    body.style.display = "none"

    // shows the main loader while loading
    mainLoader = document.getElementById("mainLoader");
    mainLoader.style.display = ""
}