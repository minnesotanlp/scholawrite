## Setting up Docker

### Requirements

* You will need to have Docker installed locally on your machine
* It may be beneficial to have DockerHub installed as well for easier observation of logging

### Running the Docker image

* Make sure you are in the `flaskapp` directory. If this is your first time running the codebase, a `docker-compose up -d` will suffice. Logging wil happen in the `flaskapp` container in DockerHub

### Seeing the output (locally) in the database

* Since you may not have the database set up in your local docker you need to set up mongodb locally
1. First, `docker exec -it mongodb bash` connect to the mongodb container
2. Once you're attached, login to admin: `mongo -u kooryan -p`
3. We want to create our collection to store our entries, so we want to create it via `use flaskdb`
4. Once we're using it create the admin `db.createUser({user: 'flaskuser', pwd: 'Cici03166201', roles: [{role: 'readWrite', db: 'flaskdb'}]})` and then exit via `exit`
5. To ensure user is created, login to it via `mongo -u flaskuser -p Cici03166201 --authenticationDatabase flaskdb`
6. Use our collection again via `use flaskdb` and in order to see entries we can utilize `db.activity.find()` to our populated database

* You can modify the admin username and password via the `Dockerfile`

### Seeing the output in the database via AWS

* WIP

### Loading and Using the Chrome Extension

Once the server is running, you can load the Chrome extension, open Overleaf in Chrome, start writing in a document, and watch the extension capture writer actions in your terminal.
* To load the Chrome extension, go to [chrome://extensions/](chrome://extensions/) in your Chrome browser. Make sure `Developer mode` is toggled on in the upper right corner. In the upper left, select `Load unpacked`. This will bring up a directory listing. Select the folder called `extension` inside your `REWARD` directory.
* Once you have loaded the extension from your directory, you can use it. Open a document in Overleaf, then click the `extensions` button in the upper right corner of your Chrome browser (the button looks like a puzzle piece). Choose ReWARD from the drop down list. Once you have selected the extension, changes you make to the document will be logged in the terminal you are running the server from. 
* As you edit your document, the changes will be logged in the database. To view these edits, run `db.activity.find()` from the mongodb container.

### Navigating between files and projects

In order to switch between Overleaf contexts (files and projects), do the following to see logging for the new context.

1. enter `db.activity.find()` into the terminal.
2. The command will show that the previous context is deleted. It will then prompt the user to `Type "it" for more`.
3. Enter `it` into the terminal. Changes for the new context will now be displayed.
