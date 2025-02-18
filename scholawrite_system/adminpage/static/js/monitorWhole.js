let idx = 0;
let arrayIdx = 0;
let globalMin = 0;
let globalMax = 499;
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

// helper function call by load_frame that fetch edits from server
async function get_frame(){
 const response = await fetch("/api/monitorwhole", {
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        method: 'POST',
        body: JSON.stringify({idx: idx}),
    });
    const message = await response.json();
    return message;
}


// load the frame based on idx
async function load_frame(){
    // If the idx exceed the range of given data, fetch from the server.
    if((idx > globalMax) || (idx < globalMin)){
        console.log("fetch!")
        pyDict = await get_frame();
        actions_obj = pyDict["actions"];
        revisions_obj = pyDict["revisions"];
        globalMin = pyDict["min"];
        globalMax = pyDict["max"]
    }
    // render the frame along with metadata
    arrayIdx = idx - globalMin
    metaBox.innerHTML = actions_obj[arrayIdx]["file"]+'<br>'+actions_obj[arrayIdx]["username"]+"<br>"+actions_obj[arrayIdx]["timestamp"]+"<br>"+idx

    contentBox.innerHTML = revisions_obj[arrayIdx]["diff_html"]

    // hides the loader
    loadBox.style.display = "none"
    // shows the button group
    buttonGroupBox.style.display = ""
    mainBox.style.display = ""

    let lineNums = revisions_obj[arrayIdx]["line_nums"]
    for (var i=0; i< lineNums.length; i++){
        lineBox.innertext = lineNums+'<br>'
    }
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

window.addEventListener('load', function() {
    metaBox = document.querySelector('#meta');
    lineBox = document.querySelector('#displayLines');
    contentBox = document.querySelector('#displayContent');
    let slider = document.getElementById("myRange");
    buttonGroupBox = document.getElementById("buttonGroup");
    mainBox = document.getElementById("mainContainer");
    loadBox =document.getElementById("loader");

    // Get the output element where the value will be displayed
    let output = document.getElementById("sliderValue");

    // generates names of the .tex
    const fileNamesArray = filenames_obj;
    console.log(fileNamesArray)
    generateButtons(fileNamesArray);

    document.querySelector('#prev').addEventListener("click", function(){
        if (idx  >0)
        {
            idx = idx - 1;
            slider.value = idx;
            load_frame().then(function() {
                generateButtons(fileNamesArray);
            })
        }
    })
    document.querySelector('#next').addEventListener("click", function(){
        if (idx  < no_of_doc)
        {
            idx = idx + 1;
            slider.value = idx;
            load_frame().then(function() {
                generateButtons(fileNamesArray);
            })
        }
    })
    document.querySelector('#jump').addEventListener("click", function(){
        let jump = document.getElementById("jumpIndex").value;
        jump = parseInt(jump)

        if (jump > no_of_doc)
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

    //load the first frame after page load
    load_frame()

    // slider
    slider.oninput = function() {
    onChangeFunction(this.value);
    };

    // Custom onchange function for slider
    function onChangeFunction(value) {
        // displays the loader
        loadBox.style.display = ""
        // hides button group
        buttonGroupBox.style.display = "none"
        mainBox.style.display = "none"

        let setIndex = parseInt(value)
        idx = setIndex
        console.log(idx)
        // load the frame and generate a new button group
        load_frame().then(function() {
            generateButtons(fileNamesArray);
        })
    }
})

// function that runs before load
window.onbeforeunload = function () {
    console.log("Unloading Loader");
    let body = document.getElementById("body");

    // hides body while loading
    body.style.display = "none";

    // shows the main loader while loading
    mainLoader = document.getElementById("mainLoader");
    mainLoader.style.display = "";
}