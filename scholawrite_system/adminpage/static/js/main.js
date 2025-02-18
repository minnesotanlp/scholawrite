const autocolors = window['chartjs-plugin-autocolors'];
Chart.register(autocolors);
let projectBox;
let contributorsBox;
let projectLoader
let contributorsLoader

function setMainLoader(){
    console.log("Unloading Loader")
    let body = document.getElementById("body");

    // hides body while loading
    body.style.display = "none"

    // shows the main loader while loading
    mainLoader = document.getElementById("mainLoader");
    mainLoader.style.display = ""
}

document.onreadystatechange = function () {
    if (document.readyState == "complete") {
        console.log("complete")

        // HTML element for loader and bar-chart
        projectBox = document.getElementById("verticalChart");
        contributorsBox = document.getElementById("horizontalChart1");
        projectLoader = document.getElementById("projectLoader");
        contributorsLoader = document.getElementById("contributorsLoader");

        if (window.location.pathname == "/project"){
            console.log("in /project")
            var trajBtn = document.getElementById("trajBtn");
            trajBtn.addEventListener("click", function() {
                // Redirect the user to monitoring page with selected project ID
                console.log("click");
                setMainLoader();
                var dropdown = document.getElementById("projectid");
                var selectedOption = dropdown.options[dropdown.selectedIndex].value;
                window.location.href = "/monitor?project_id="+selectedOption;
            });
        }
        var ctx = document.getElementById('verticalChart').getContext('2d');
        var stackedBarChart = new Chart(ctx, {
            type: 'bar',
            data: dataArray[0],
            options: {
                scales: {
                    x: { stacked: true },
                    y: { stacked: true }
                }
            }
        });

        // shows the charts after loading
        projectBox.style.display = ""
        contributorsBox.style.display = ""
    
        // shows the loaders after loading
        projectLoader.style.display = "none"
        contributorsLoader.style.display = "none"    

        var ctx = document.getElementById('horizontalChart1').getContext('2d');
        var stackedBarChart = new Chart(ctx, {
            type: 'bar',
            data: dataArray[1],
            options: {
                indexAxis: 'y',
                scales: {
                    x: { stacked: true },
                    y: { stacked: true }
                }
            }
        });
        if (window.location.pathname == "/main" || window.location.pathname == "/"){
            var ctx = document.getElementById('horizontalChart2').getContext('2d');
            var stackedBarChart = new Chart(ctx, {
                type: 'bar',
                data: dataArray[2],
                options: {
                    indexAxis: 'y',
                    scales: {
                        x: { stacked: true },
                        y: { stacked: true }
                    }
                }
            });
        }
    }
}

// function that runs before load
window.onbeforeunload = function () {
    console.log("Loading Projects")
    // hides the charts while loading
    document.querySelectorAll('canvas').forEach(function(canvas) {
        canvas.style.display = 'none';
    });

    // shows the loaders while loading
    document.querySelectorAll('.loader').forEach(function(canvas) {
        canvas.style.display = '';
    });
}