let serverURL;
let usernameInput;
let projectIDs;
//serverURL = "http://127.0.0.1:5000"
serverURL = "https://scholawrite.ngrok.app/"

chrome.storage.local.get(["projectIDs"], async function(result){
    projectIDs = result.projectIDs;
    console.log(projectIDs);
});

function clearProjectIds(){
    let container = document.getElementsByClassName("scroll-container")[0];
    let entries = container.children;
    for (var i = entries.length - 2; i > 0; i--) {
        container.removeChild(entries[i]);
    }
    document.getElementById("textAtTop").value = "";
}

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

    var dividers = document.querySelectorAll('.divider');
    if (dividers !== null){
        dividers.forEach((node) => {
            node.style.margin = "20px 0";
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

function addTextBox(innerID) {
    const target = document.getElementById("add");
    const textboxContainer = document.createElement('div');
    const scrollContainer = document.getElementsByClassName('scroll-container')[0];
    textboxContainer.className = 'textbox-container';

    const textBox = document.createElement('input');
    textBox.type = 'text';
    textBox.className = 'textbox';
    textBox.value = innerID;

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
            chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
                chrome.tabs.sendMessage(tabs[0].id, {source: "username", username: usernameInput}, function (response) {
                });
            });
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
//        chrome.runtime.sendMessage({message: "logout"});
//        regForm.style.display = "none";
//        welcomeMessage.style.display = "none";
//        logout.style.display = "none";
//        loginForm.style.display = "block";
//        clearProjectIds();
        checkbox.checked = false;
//        chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
//            chrome.tabs.sendMessage(tabs[0].id, {toggle: checkbox.checked}, function (response) {
//            });
//        });
        chrome.storage.local.set({'enabled': checkbox.checked }, function () {
            console.log("confirmed");
        });
        chrome.storage.local.set({"projectIDs": []}, function() {
            console.log('project IDs removed successfully!');
        })
        location.reload();
    });


    // section for handling login
    // 100: Wrong username/password
    // 200: User already exist
    // 300: pass
    // 400: server error
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
            var json, status;
            json = await postWriterText(1, {state: "login", username: usernameInput, password: passwordInput});
            status = json.status;
            if (status == 300){
                chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
                    chrome.tabs.sendMessage(tabs[0].id, {source: "username", username: usernameInput}, function (response) {
                    });
                });
                chrome.storage.local.set({'username': usernameInput}, function() {
                  console.log('Data saved successfully!');
                });
                loginForm.style.display = "none";
                welcomeMessage.innerHTML = "Welcome, " + usernameInput;
                welcomeMessage.style.display = "block";
                logout.style.display = "block";
                chrome.runtime.sendMessage({message: "username", username: usernameInput});
            }
            else if (status == 100){
                showError(1, login, "Incorrect username/password, please try again");
            }
            else if (status == 400){
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
            var json, status
            json = await postWriterText(1, {state: "register", username: usernameInput, password: passwordInput});
            status = json.status;
            if (status == 300){
                chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
                    chrome.tabs.sendMessage(tabs[0].id, {source: "username", username: usernameInput}, function (response) {
                    });
                });
                chrome.storage.local.set({'username': usernameInput}, function() {
                    console.log('username saved successfully!');
                });
                regForm.style.display = "none";
                welcomeMessage.innerHTML = "Welcome, " + usernameInput;
                welcomeMessage.style.display = "block";
                logout.style.display = "block";
                chrome.runtime.sendMessage({message: "username", username: usernameInput});
            }
            else if (status == 200){
                showError(1, register, "User already exist, choose another name or login");
            }
            else if(status == 400){
                showError(1, register, "Sever error encountered, please try later");
            }
        }
    });
    gl.addEventListener('click', function(){
        clearError();
        document.documentElement.style.maxHeight = "410px";
        regForm.style.display = "none";
        loginForm.style.display = "block";
    });
});

async function postWriterText(task, activity) {
    try {
        if (task === 1){
            const response = await fetch(serverURL + "/users", {
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
            return message
        }
    }
    catch (err){
        console.log('failed to fetch');
        return {status: 500};
    }
}
