from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
import secrets
from deta import Drive
from os import getenv
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse, StreamingResponse, FileResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

load_dotenv()

ADMIN_USERNAME = getenv("ADMIN_USERNAME", "demo")
ADMIN_PASSWORD = getenv("ADMIN_PASSWORD", "demo")

demo_credentials_part = ""
if (ADMIN_USERNAME == "demo"):
    demo_credentials_part = """
### Demo Credentials    
* **Username:** demo
* **Password:** demo

"""
description_of_fastapi = f"""
       

## Simple and beautiful dashboard to keep your files safe.

{demo_credentials_part}

## [You can add your files as private or public just look **_File Upload Part_** ⬇️](#operations-tag-File_Upload)

* **ADMIN_USERNAME** and **ADMIN_PASSWORD** (which is asked on deployment) is used as password and username 
* Private Files can only be accessible with your username and password

# [Show All Files 🗂️](get-files)  
  


# Deployment 💻 
You can deploy your own instance of PersonalDrive using the button below. You will need a [Deta](https://www.deta.sh/) account.  
[![Click Here To Deploy Your Own Personal Drive 💻️](https://button.deta.dev/1/svg)](https://go.deta.dev/deploy?repo=https://github.com/mehmetcanfarsak/PersonalDrive)


"""

app = FastAPI(description=description_of_fastapi, title="Personal Drive 📁",
              contact={"url": "https://github.com/mehmetcanfarsak", "Name": "Mehmet Can Farsak"})
security = HTTPBasic()

class AdminUser(BaseModel):
    username: str
    password: str


def get_admin_user(credentials: HTTPBasicCredentials = Depends(security)):
    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = ADMIN_USERNAME.encode("utf8")
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = ADMIN_PASSWORD.encode("utf8")
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return AdminUser(username=correct_username_bytes.decode(),password=correct_password_bytes.decode())




app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates("templates")

personal_drive_files = Drive('PersonalDriveFiles')


@app.get("/", include_in_schema=False, response_class=RedirectResponse)
def root():
    return RedirectResponse("/docs")


@app.post("/public-file",
          description="You can upload new file or change existing file with selecting file with the same name.",
          tags=["File Upload"])
def upload_publicly_accessible_file(request: Request, credentials: HTTPBasicCredentials = Depends(get_admin_user),
                                    file: UploadFile = File()):
    if (credentials.username == "demo"):
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE,
                            detail="You can not upload/delete files in demo. Please follow instructions to deploy your Personal Drive at github.com/mehmetcanfarsak/PersonalDrive", )
    personal_drive_files.put("public/" + file.filename, file.file)
    return "https://" + request.headers.get("host") + "/" + file.filename


@app.post("/private-file",
          description="You can upload new file or change existing file with selecting file with the same name",
          tags=["File Upload"])
def upload_privately_accessible_file(request: Request, credentials: HTTPBasicCredentials = Depends(get_admin_user),
                                     file: UploadFile = File()):
    if (credentials.username == "demo"):
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE,
                            detail="You can not upload/delete files in demo. Please follow instructions to deploy your Personal Drive at github.com/mehmetcanfarsak/PersonalDrive", )
    personal_drive_files.put("private/" + file.filename, file.file)
    return "https://" + request.headers.get("host") + "/" + file.filename


@app.get("/get-files", response_class=HTMLResponse, tags=["Get Files"])
def get_files_result_in_html_format(request: Request, credentials: HTTPBasicCredentials = Depends(get_admin_user)):
    drive_files = personal_drive_files.list()
    private_files = []
    public_files = []

    for drive_file in drive_files['names']:
        if (str(drive_file).startswith("private/")):
            private_files.append(drive_file)
        if (str(drive_file).startswith("public/")):
            public_files.append(drive_file)
    return templates.TemplateResponse("get-files.html", {"request": request, "private_files": private_files,
                                                         "public_files": public_files})


@app.post("/get-files", response_class=JSONResponse, tags=["Get Files"])
def get_files_result_in_json_format(credentials: HTTPBasicCredentials = Depends(get_admin_user)):
    return personal_drive_files.list()


@app.get("/public-file/{file_name}", response_class=StreamingResponse, tags=["Download / Show File"])
def show_public_file(file_name: str):
    file = personal_drive_files.get("public/" + file_name)
    if (not file):
        raise HTTPException(status_code=404, detail="File Not Found!")
    return StreamingResponse(file.iter_chunks(1024), media_type="")


@app.get("/private-file/{file_name}", response_class=StreamingResponse, tags=["Download / Show File"])
def show_private_file(file_name: str, credentials: HTTPBasicCredentials = Depends(get_admin_user)):
    file = personal_drive_files.get("private/" + file_name)
    if (not file):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File Not Found!")
    return StreamingResponse(file.iter_chunks(1024), media_type="")


@app.post("/delete-public-file/{file_name}", tags=["Delete File"])
def delete_publicly_accessible_file(file_name: str, credentials: HTTPBasicCredentials = Depends(get_admin_user)):
    if (credentials.username == "demo"):
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE,
                            detail="You can not upload/delete files in demo. Please follow instructions to deploy your Personal Drive at github.com/mehmetcanfarsak/PersonalDrive", )
    personal_drive_files.delete("public/" + file_name)
    return "success"


@app.post("/delete-private-file/{file_name}", tags=["Delete File"])
def delete_private_accessible_file(file_name: str, credentials: HTTPBasicCredentials = Depends(get_admin_user)):
    if (credentials.username == "demo"):
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE,
                            detail="You can not upload/delete files in demo. Please follow instructions to deploy your Personal Drive at github.com/mehmetcanfarsak/PersonalDrive", )
    personal_drive_files.delete("private/" + file_name)
    return "success"


@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")
