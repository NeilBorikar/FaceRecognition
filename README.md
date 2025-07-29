# FaceRecognition
This is an facerecognition attendance system where the complete backend is written in python and for front end HTML,JS and CSS is used.

THE SETUP IS AS FOLLOWS:
in order to Make this project run.It's recommended to use python interpreter 3.11.8 which you can install from the link
( https://www.python.org/downloads/release/python-3118/) make sure to click set path while downloading
then in  VScode download following extensions:
Python
Pylance
Jinja
Flask Snippets
Live Server
GitLens
further in VScode press ctrl + shift + p
then type "Python:Interpreter"
and then select the path mentioning python 3.11.8
(Python 3.11.8 C:\Program Files\Python311\python.exe).Which may look someting like this.
then install all the libraries used in the code.

FOLDER STRUCTURE:
First create an folder 
"face_recognition_attendance"(or anything you like)
inside that folder store files
app.py
attendance_system.py
database.py
fix_encodings.py
MAKE SURE ALL FILES ARE ".py " FILES AND NOT ".txt" FILES

Then inside are face_recognition_attendance folder create another folder named "templates"
inside templates we will be storing all our HTML files:
base.html
index.html
attendance.html
register.html
users.html

then inside face_recognition_attendance only create another folder named "static".
inside static create three folders named :
"css"
"images"
"js"

inside "css":
store "style.css"file

inside "images"
store "empty.svg"file

inside "js"
store "script.js"
and this will be your complete folder structure 

RUNNING THE PROJECT:
In VS code go to file section at the top of your screen to your left.
in that go to open new folder,Navigate to your face_recognition_attendance folder.
then in terminal type:
"python app.py"
then you will see something like this:
Serving Flask app 'app'
 * Debug mode: on
   After this go to chrome and paste:
   (http://127.0.0.1:5000/)
This will open the Face Attendance website.
and then proceed to explore the website and it's functionalities.


