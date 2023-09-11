let serverURL;
let usernameInput;
serverURL = " http://127.0.0.1:5000"

function clearError(){
    var errMessage = document.querySelectorAll('p[style="color: red; font-size: 14px;"]');
    console.log("here")
    if (errMessage !== null){
        errMessage.forEach((node) => {
            node.parentNode.removeChild(node);
        });
    }
    var notiMessage = document.querySelectorAll('p[style="color: black; font-size: 14px;"]');
    if (notiMessage !== null){
        notiMessage.forEach((node) => {
            node.parentNode.removeChild(node);
        });
    }
};

function showError(pos, node, text){
    var textElement = document.createElement("p");
    textElement.innerText = text;
    textElement.style.color = "red";
    textElement.style.fontSize = "14px";
    if (pos === 1){
        node.parentNode.insertBefore(textElement, node);
    }
    else if (pos === 2){
        node.parentNode.insertBefore(textElement, node.nextElementSibling);
    }
}

function addTextBox(event) {
    const target = event.target;
    const scrollContainer = document.getElementsByClassName('scroll-container')[0];
    const textboxContainer = document.createElement('div');
    textboxContainer.className = 'textbox-container';

    const textBox = document.createElement('input');
    textBox.type = 'text';
    textBox.className = 'textbox';

    const deleteButton = document.createElement('button');
    deleteButton.textContent = 'Delete';
    deleteButton.className = 'del';
    deleteButton.onclick = function() {
        scrollContainer.removeChild(textboxContainer);
    };

    textboxContainer.appendChild(textBox);
    textboxContainer.appendChild(deleteButton);
    scrollContainer.insertBefore(textboxContainer, target);
}

document.addEventListener('DOMContentLoaded', function () {
    var checkbox = document.querySelector('input[type="checkbox"]');
    var loginForm = document.getElementById("loginForm");
    var regForm = document.getElementById("regForm");
    var logout = document.getElementById("lo");
    var welcomeMessage = document.getElementById("welcomeMessage");

    chrome.storage.local.get(['username'], function(result) {
        if (result.username !== undefined){
            loginForm.style.display = "none";
            usernameInput = result.username;
            welcomeMessage.innerHTML = "Welcome, " + result.username;
            welcomeMessage.style.display = "block";
            logout.style.display = "block";
        }
    });
    chrome.storage.local.get('enabled', function (result) {
        if (result.enabled != null) {
            checkbox.checked = result.enabled;
        }
        chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
            chrome.tabs.sendMessage(tabs[0].id, {toggle: checkbox.checked}, function (response) {
            });
        });
    });

    checkbox.addEventListener('click', async function () {
        clearError();
        var tempUsername = "";
        chrome.storage.local.get(['username'], function(result) {
            console.log(result);
            tempUsername = result.username;
            if ((tempUsername === "" || tempUsername === undefined) && checkbox.checked==true){
                var target = document.getElementsByClassName("sliderWrapper")[0]
                showError(2, target, "Please login/register before turn on the switch");
                checkbox.checked = false;
            }
            else {
                console.log(checkbox.checked);
                chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
                    chrome.tabs.sendMessage(tabs[0].id, {toggle: checkbox.checked}, function (response) {
                    });
                });
                chrome.storage.local.set({ 'enabled': checkbox.checked }, function () {
                    console.log("confirmed");
                });
            }
        });
    });

    // section for handling logout
    logout.addEventListener('click', function(){
        chrome.storage.local.remove('username', function() {
            console.log('Item has been removed from local storage');
        });
        chrome.runtime.sendMessage({message: "logout"});
        regForm.style.display = "none";
        welcomeMessage.style.display = "none";
        logout.style.display = "none";
        loginForm.style.display = "block";
    });

    // section for handling projectIDs
    var manageIDs = document.getElementById("manageIDs");
    var back = document.getElementById("back");

    manageIDs.addEventListener('click', async function(){
        clearError();
        var tempUsername = ""
        chrome.storage.local.get(['username'], function(result) {
            tempUsername = result.username;
            if (tempUsername === "" || tempUsername === undefined){
                showError(2, manageIDs, "Please login/register before manage your IDs");
            }
            else {
                document.getElementById("control").style.display="none";
                document.getElementById("manage").style.display="grid";
            }
        });
    });
    back.addEventListener('click', function(){
        document.getElementById("manage").style.display="none";
        document.getElementById("control").style.display="block";
    });

    // section for handling login
    var login = document.querySelector('button[type="submit"][id="log"]');
    var username = document.getElementById("username");
    var password = document.getElementById("password");
    var gr = document.getElementById("gr");

    username.addEventListener('click', clearError);
    password.addEventListener('click', clearError);

    login.addEventListener('click', async function(){
        clearError();
        usernameInput = username.value;
        var passwordInput = password.value;
        if (usernameInput == "" || passwordInput == ""){
            showError(1, login, "Invalid username/password, please try again");
        }
        else {
            var code = 400;
            code = await postWriterText(1, {state: "login", username: usernameInput, password: passwordInput});
            code = 300;
            if (code == 300){
                chrome.storage.local.set({'username': usernameInput}, function() {
                  console.log('Data saved successfully!');
                });
                loginForm.style.display = "none";
                welcomeMessage.innerHTML = "Welcome, " + usernameInput;
                welcomeMessage.style.display = "block";
                logout.style.display = "block";
                chrome.runtime.sendMessage({message: "username", username: usernameInput});
            }
            else if (code == 100){
                showError(1, login, "Incorrect username/password, please try again");
            }
            else if (code == 400){
                showError(1, login, "Sever error encountered, please try again");
            }
        }
    });
    gr.addEventListener('click', function(){
        clearError();
        document.documentElement.style.maxHeight = "460px";
        regForm.style.display = "block";
        loginForm.style.display = "none";
    });

    // section for handling registration
    var register = document.querySelector('button[type="submit"][id="reg"]');
    var newUser = document.getElementById("newUser");
    var newPass = document.getElementById("newPass");
    var confirmPass = document.getElementById("confirmPass");
    var gl = document.getElementById("gl");

    newUser.addEventListener('click', clearError);
    newPass.addEventListener('click', clearError);
    confirmPass.addEventListener('click', clearError);

    register.addEventListener('click', async function(){
    	clearError();
        usernameInput = newUser.value;
        var passwordInput = newPass.value;
        var confirmPassInput = confirmPass.value;
        if (usernameInput == "" || passwordInput == "" || confirmPassInput == ""){
            showError(1, register, "Invalid username/password, please try again");
        }
        else if (passwordInput !== confirmPassInput){
            showError(1, register, "Two passwords mismatch, please try again");
        }
        else {
            var match = 400
            match = await postWriterText(1, {state: "register", username: usernameInput, password: passwordInput});
            if (match == 300){
                chrome.storage.local.set({'username': usernameInput}, function() {
                  console.log('Data saved successfully!');
                });
                regForm.style.display = "none";
                welcomeMessage.innerHTML = "Welcome, " + usernameInput;
                welcomeMessage.style.display = "block";
                logout.style.display = "block";
                chrome.runtime.sendMessage({message: "username", username: usernameInput});
            }
            else if (match == 200){
                showError(1, register, "User already exist, choose another name or login");
            }
            else if(match == 400){
                showError(1, register, "Sever error encountered, please try again");
            }
        }
    });
    gl.addEventListener('click', function(){
        clearError();
        document.documentElement.style.maxHeight = "410px";
        regForm.style.display = "none";
        loginForm.style.display = "block";
    });

    //section to manage tracking project IDs
    const add = document.getElementById("add");
    add.addEventListener("click", addTextBox);
    const del = document.getElementById("deleteAtTop");
    del.addEventListener("click", function(event){
        event.target.previousElementSibling.value = "";
    });

    const save = document.getElementById("save");
    save.addEventListener("click", async function(){
        buttons_and_inputs= document.getElementById("manage").querySelectorAll('*');
        buttons_and_inputs.forEach(function (element) {
            element.disabled = true;
        });
        document.getElementById("manage").style.filter = "blur(3Px)";
        document.getElementById("spinner").style.display = "block";
        var projectIDs = []
        textboxContainers = document.getElementsByClassName("textbox-container");
        for (var i = 0; i<textboxContainers.length; i++){
            if (textboxContainers[i].children[0].value !== ""){
                projectIDs.push(textboxContainers[i].children[0].value);
            }
        }
        console.log(projectIDs);
        await postWriterText(2, {username: usernameInput, project_IDs: projectIDs});
        buttons_and_inputs.forEach(function (element) {
            element.removeAttribute('disabled');
        });
        document.getElementById("manage").style.filter = "";
        document.getElementById("spinner").style.display = "none";
    });
});

async function postWriterText(task, activity) {
    try {
        if (task === 1){
            const response = await fetch(serverURL + "/ReWARD/system", {
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
            // 100: Wrong username/password
            // 200: User already exist
            // 300: pass
            // 400: server error
            return message.status
        }
        else if (task === 2){
            const response = await fetch(serverURL + "/ReWARD/ids", {
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
            // 100: Wrong username/password
            // 200: User already exist
            // 300: pass
            // 400: server error
            return message.status
        }
    }
    catch (err){
        console.log('failed to fetch');
        return 400;
    }
}
