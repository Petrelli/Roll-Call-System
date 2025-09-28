from fastapi import FastAPI, HTTPException, Depends, Response, Request
from fastapi.security import HTTPBasic
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import random
import csv
import json
import os

app = FastAPI()

# Static files configuration
app.mount("/static", StaticFiles(directory="static"), name="static")

# File paths
STUDENTS_FILE = "students.txt"
ABSENT_RECORDS_FILE = "absent_students.json"

students = []
called_students = []
absent_records = {}

# Security
security = HTTPBasic()

# Global variable to store session cookie
SESSION_COOKIE = "auth_session"


# Load students list from file
def load_students_from_file(file):
    global students, called_students
    with open(file, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        students = [{'id': row[0], 'name': row[1]} for row in reader if row]  # Ignore empty rows
    called_students = []


# Load absent records
def load_absent_records():
    global absent_records
    if os.path.exists(ABSENT_RECORDS_FILE):
        with open(ABSENT_RECORDS_FILE, 'r', encoding='utf-8') as f:
            try:
                absent_records = json.load(f)
            except json.JSONDecodeError:
                absent_records = {}


# Save absent records to file
def save_absent_records():
    with open(ABSENT_RECORDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(absent_records, f, ensure_ascii=False, indent=4)


# Initialize data
load_students_from_file(STUDENTS_FILE)
load_absent_records()


# Serve login page
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html lang="cn">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>登录</title>
        <style>
            body {
                font-family: '微软雅黑', sans-serif;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background-color: #f0f8ff;
            }
            input {
                font-size: 1em;
                margin: 10px 0;
                padding: 10px;
                width: 200px;
                border: 1px solid #ccc;
                border-radius: 5px;
            }
            button {
                font-size: 1.2em;
                padding: 10px 20px;
                margin: 5px;
                background-color: #008CBA;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }
        </style>
        <script>
            async function login() {
                const username = document.getElementById("username").value;
                const password = document.getElementById("password").value;
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                if (response.ok) {
                    window.location.href = "/main";  // Redirect to main page
                } else {
                    alert("登录失败，用户名或密码错误。");
                }
            }
        </script>
    </head>
    <body>
        <h1>欢迎来到学生点名系统</h1>
        <input type="text" id="username" placeholder="用户名" required>
        <input type="password" id="password" placeholder="密码" required>
        <button onclick="login()">登录</button>
    </body>
    </html>
    """


# Serve main page after login
@app.get("/main", response_class=HTMLResponse)
async def main_page(request: Request):
    session_cookie = request.cookies.get(SESSION_COOKIE)
    if session_cookie != "authenticated":
        raise HTTPException(status_code=401, detail="未认证，访问被拒绝。")

    return """
    <!DOCTYPE html>
    <html lang="cn">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>随机抽取一名幸运观众</title>
        <style>
            body {
                font-family: '微软雅黑', sans-serif;
                background-color: #f0f8ff;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            img {
                width: 150px;
                margin-bottom: 20px;
            }
            h1 {
                color: #4b0082;
                font-size: 4em;
            }
            #picked-student {
                font-size: 3em;
                color: #9932cc;
                margin: 20px 0;
            }
            button {
                font-size: 1.2em;
                padding: 10px 20px;
                margin: 5px;
                background-color: #008CBA;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }
            button:hover {
                background-color: #005f73;
            }
        </style>
        <script>
            let animationInterval;
            let allStudents = [];

            // 页面加载时获取学生名单
            window.onload = async function() {
                const response = await fetch('/get_students');
                if (response.ok) {
                    const data = await response.json();
                    allStudents = data.students;
                } else {
                    alert("获取学生名单失败，请重新登录");
                }
            };

            async function pickRandomStudent() {
                if (allStudents.length === 0) {
                    alert("没有学生可以抽取了。");
                    return;
                }

                // 1. 动画效果：快速滚动 2 秒
                let duration = 2000;
                let intervalTime = 100;

                clearInterval(animationInterval);

                animationInterval = setInterval(() => {
                    const randomIndex = Math.floor(Math.random() * allStudents.length);
                    const fakeStudent = allStudents[randomIndex];
                    document.getElementById('picked-student').innerText =
                        fakeStudent ? `${fakeStudent.id}: ${fakeStudent.name}` : "抽取中...";
                }, intervalTime);

                // 2. 两秒后调用后端接口，得到最终结果
                setTimeout(async () => {
                    clearInterval(animationInterval);

                    const response = await fetch('/random_pick', { method: 'POST' });
                    if (response.ok) {
                        const data = await response.json();
                        const pickedStudent = `${data.picked_student.id}: ${data.picked_student.name}`;
                        document.getElementById('picked-student').innerText = pickedStudent;

                        // 更新前端名单，避免重复
                        allStudents = allStudents.filter(s => s.id !== data.picked_student.id);
                    } else {
                        const errorData = await response.json();
                        alert(errorData.detail);
                    }
                }, duration);
            }

            async function markAbsent() {
                const studentInfo = document.getElementById('picked-student').innerText.split(": ");
                if (studentInfo.length === 2) {
                    const student = { id: studentInfo[0], name: studentInfo[1] };
                    const response = await fetch('/mark_absent', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(student)
                    });
                    const data = await response.json();
                    alert(data.message);
                } else {
                    alert("请先抽取一名学生");
                }
            }

            async function resetStudents() {
                const response = await fetch('/reset', { method: 'POST' });
                const data = await response.json();
                alert(data.message);

                const res = await fetch('/get_students');
                if (res.ok) {
                    const d = await res.json();
                    allStudents = d.students;
                }
            }
        </script>
    </head>
    <body>
        <img src="/static/logo.png" alt="Nanjing University of Posts and Telecommunications Logo">
        <h1>随机抽取一名幸运观众</h1>
        <div id="picked-student">幸运观众:</div>
        <button onclick="pickRandomStudent()">抽取</button>
        <button onclick="markAbsent()">缺席</button>
        <button onclick="resetStudents()">重置</button>
    </body>
    </html>
    """


# 登录接口
@app.post("/login")
async def login(response: Response, credentials: dict):
    username = credentials.get('username')
    password = credentials.get('password')
    if username == "user" and password == "password":
        response.set_cookie(key=SESSION_COOKIE, value="authenticated")
        return {"message": "Authentication successful, session cookie set."}
    raise HTTPException(status_code=401, detail="Unauthorized")


# 获取学生列表
@app.get("/get_students")
async def get_students(request: Request):
    session_cookie = request.cookies.get(SESSION_COOKIE)
    if session_cookie != "authenticated":
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"students": students}


# 随机抽取学生
@app.post("/random_pick")
async def pick_random_student(request: Request):
    session_cookie = request.cookies.get(SESSION_COOKIE)
    if session_cookie != "authenticated":
        raise HTTPException(status_code=401, detail="Unauthorized")

    if len(students) == 0:
        raise HTTPException(status_code=404, detail="没有学生可以抽取了。")
    picked_student = random.choice(students)
    students.remove(picked_student)
    return {"picked_student": picked_student}


# 标记缺席
@app.post("/mark_absent")
async def mark_absent(student: dict, request: Request):
    session_cookie = request.cookies.get(SESSION_COOKIE)
    if session_cookie != "authenticated":
        raise HTTPException(status_code=401, detail="Unauthorized")

    key = f"{student['id']}: {student['name']}"
    if key in absent_records:
        absent_records[key] += 1
    else:
        absent_records[key] = 1
    save_absent_records()
    return {"message": f"{student['name']} 缺席已记录。"}


# 重置学生名单
@app.post("/reset")
async def reset_students():
    load_students_from_file(STUDENTS_FILE)
    return {"message": "学生列表已重置。"}
