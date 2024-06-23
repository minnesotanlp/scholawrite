## About

Web application modified based on pdf.js [demo](https://mozilla.github.io/pdf.js/web/viewer.html) to visualize the text creation process of each section in a paper. Most files have been removed, only leaving nessecery files for pdf display.

Data needed to run the web app:
1. Scholawrite dataset
2. Pdf file of a paper generated from latex compiler
3. SyncTex file of a paper generated from latex compiler

## How to Run

Follow these steps to get started:

Use Flask:
1. Install Flask bu running: `pip install flask`
2. Rin the application: `python3 render.py`

Use Live Server:
1. Make sure you have **Live Server** installed from the VSCode extension marketplace.
2. Open this project in the VSCode. Go to `pdf.js-4.3.136\web` folder and oepn `viewer.html` in the editor.
3. Click the **Go Live** button in the lower-right corner of the VSCode window.
4. A browser tab should pop-up automatically. If it doesn't, navigate to `http://localhost:5500/pdf.js-4.3.136/web/viewer.html` in your browser.

## Credit

This project uses [pdf.js](https://github.com/mozilla/pdf.js/releases/tag/v4.3.136) by Mozilla.