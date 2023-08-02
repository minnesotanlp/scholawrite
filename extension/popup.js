let serverURL;
serverURL = ""

function clearError(){
    var errMessage = document.querySelectorAll('p[style="color: red; font-size: 14px;"]');
    console.log("here")
    if (errMessage !== null){
        errMessage.forEach((node) => {
            node.parentNode.removeChild(node);;
        });
    }
    var notiMessage = document.querySelectorAll('p[style="color: black; font-size: 14px;"]');
    if (notiMessage !== null){
        notiMessage.forEach((node) => {
            node.parentNode.removeChild(node);;
        });
    }
};

function showError(node, text){
    var textElement = document.createElement("p");
    textElement.innerText = text;
    textElement.style.color = "red";
    textElement.style.fontSize = "14px";
    node.parentNode.insertBefore(textElement, node);
}

document.addEventListener('DOMContentLoaded', function () {
    var checkbox = document.querySelector('input[type="checkbox"]');
    var loginForm = document.getElementById("loginForm");
    var regForm = document.getElementById("regForm");
    var logout = document.getElementById("lo");
    var welcomeMessage = document.getElementById("welcomeMessage");
    var sendURL = document.getElementById("sendURL");
    var server = document.getElementById("serverURL");

    chrome.storage.local.get(['username'], function(result) {
        if (result.username !== undefined){
            loginForm.style.display = "none";
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

    chrome.storage.local.get('server', function (result) {
        if (result.server !== undefined && result.server !== ""){
            serverURL = result.server;
            server.value = serverURL;
        }
    });

    checkbox.addEventListener('click', function () {
        console.log(checkbox.checked);
        chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
            chrome.tabs.sendMessage(tabs[0].id, {toggle: checkbox.checked}, function (response) {
            });
        });
        chrome.storage.local.set({ 'enabled': checkbox.checked }, function () {
            console.log("confirmed");
        });
    });

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

    server.addEventListener('click', clearError);

    sendURL.addEventListener('click', function(){
        var URLInput = server.value;
        clearError();
        if (URLInput == ""){
            showError(sendURL.nextSibling, "Invalid saver URL, please try again");
        }
        else{
            serverURL = URLInput;
            chrome.runtime.sendMessage({message: "serverURL", serverURL: URLInput});
            chrome.storage.local.set({'server': URLInput}, function() {
                  console.log('Sever URL saved successfully!');
            });
            var te = document.createElement("p");
            te.innerText = "Successfully set up server URL!";
            te.style.color = "black";
            te.style.fontSize = "14px";
            sendURL.parentNode.insertBefore(te, sendURL.nextSibling);
        }
    });

    var login = document.querySelector('button[type="submit"][id="log"]');
    var username = document.getElementById("username");
    var password = document.getElementById("password");
    var gr = document.getElementById("gr");

    username.addEventListener('click', clearError);
    password.addEventListener('click', clearError);

    login.addEventListener('click', async function(){
        clearError();
        var usernameInput = username.value;
        var passwordInput = password.value;
        if (usernameInput == "" || passwordInput == ""){
            showError(login, "Invalid username/password, please try again");
        }
        else {
            var code =400;
            code = await postWriterText({state: "login", username: usernameInput, password: passwordInput});
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
                showError(login, "Incorrect username/password, please try again");
            }
            else if (code == 400){
                showError(login, "Sever error encountered, please try again");
            }
        }
    });
    gr.addEventListener('click', function(){
        clearError();
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
        var usernameInput = newUser.value;
        var passwordInput = newPass.value;
        var confirmPassInput = confirmPass.value;
        if (usernameInput == "" || passwordInput == "" || confirmPassInput == ""){
            showError(register, "Invalid username/password, please try again");
        }
        else if (passwordInput !== confirmPassInput){
            showError(register, "Two passwords mismatch, please try again");
        }
        else {
            var match = 400
            match = await postWriterText({state: "register", username: usernameInput, password: passwordInput});
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
                showError(register, "User already exist, choose another name or login");
            }
            else if(match == 400){
                showError(register, "Sever error encountered, please try again");
            }
        }
    });
    gl.addEventListener('click', function(){
        clearError();
        regForm.style.display = "none";
        loginForm.style.display = "block";
    });
});

async function postWriterText(activity) {
    try {
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
    catch (err){
        console.log('failed to fetch');
        return 400;
    }
}
