let passwordElement, confirmPasswordElement

function clearError(){
    var errMessage = document.querySelectorAll('p[style="color: red; font-size: 14px;"]');
    if (errMessage !== null){
        errMessage.forEach((node) => {
            node.parentNode.removeChild(node);
        });
    }
}

function showError(pos, node, text){
    var textElement = document.createElement("p");
    textElement.innerText = text;
    textElement.style.color = "red";
    textElement.style.fontSize = "14px";
    textElement.style.margin = "0 0 10px 0";
    if (pos === 1){
        node.parentNode.insertBefore(textElement, node);
    }
    else if (pos === 2){
        node.parentNode.insertBefore(textElement, node.nextElementSibling);
    }
}

function validateForm() {
    password = passwordElement.value
    confirmPassword = confirmPasswordElement.value
    if (password !== confirmPassword) {
        showError(1, document.getElementById('submit'), "Passwords do not match. Please try again.")
        return false;
    }

  // If the values are the same, allow the form to be submitted
  return true;
}

document.addEventListener('DOMContentLoaded', function () {
    passwordElement = document.getElementById('password');
    confirmPasswordElement = document.getElementById('confirmPassword');
    passwordElement.addEventListener('click', clearError);
    confirmPasswordElement.addEventListener('click', clearError);

    button = document.getElementById('submit');
    button.addEventListener('click', clearError);
})