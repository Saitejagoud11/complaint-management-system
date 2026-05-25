from flask import Flask, render_template, request, redirect, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
import base64
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

# ================= DATABASE =================
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Saiteja@1432",
    database="hostel_complaint_db"
)
cursor = db.cursor(dictionary=True)

# ================= HOME =================
@app.route("/")
def home():
    return render_template("home.html")

# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = generate_password_hash(request.form.get("password"))

        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        if cursor.fetchone():
            return "Username already exists"

        cursor.execute(
            "INSERT INTO users (username,email,password,role) VALUES (%s,%s,%s,%s)",
            (username, email, password, "student")
        )
        db.commit()
        return redirect("/login")

    return render_template("register.html")

# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user["password"], password):
            session["user"] = user["username"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect("/admin")
            else:
                return redirect("/student")
        else:
            return "Invalid username or password"

    return render_template("login.html")

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ================= STUDENT DASHBOARD =================
@app.route("/student")
def student():
    if "user" not in session:
        return redirect("/login")

    cursor.execute(
        "SELECT * FROM complaints WHERE student=%s",
        (session["user"],)
    )
    complaints = cursor.fetchall()

    return render_template("studentdashboard.html", complaints=complaints)

# ================= SUBMIT COMPLAINT =================
@app.route("/submit-complaint", methods=["GET", "POST"])
def submit_complaint():
    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":
        ctype = request.form.get("complaint_type")
        desc = request.form.get("description")

        # ================= RULE BASED PRIORITY =================
        if "electric" in desc.lower() or "power" in desc.lower():
            priority = "High"
        elif "water" in desc.lower():
            priority = "Medium"
        else:
            priority = "Low"

        # ================= IMAGE =================
        image_file = request.files.get("image")
        image_name = None
        if image_file and image_file.filename != "":
            image_name = secure_filename(image_file.filename)
            image_file.save(os.path.join("static/uploads", image_name))

        # ================= VOICE =================
        voice_data = request.form.get("voice_data")
        voice_file = None
        if voice_data:
            header, encoded = voice_data.split(",", 1)
            audio_bytes = base64.b64decode(encoded)
            voice_file = f"{uuid.uuid4()}.webm"
            with open("static/uploads/" + voice_file, "wb") as f:
                f.write(audio_bytes)

        # ================= ANONYMOUS =================
        is_anonymous = request.form.get("is_anonymous")

        if is_anonymous:
            student_name = "Anonymous"
            is_anonymous_flag = True
        else:
            student_name = session["user"]
            is_anonymous_flag = False

        # ================= INSERT =================
        cursor.execute("""
            INSERT INTO complaints
            (complaint_type, description, priority, status,
             image, voice, student, created_time, is_anonymous)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            ctype,
            desc,
            priority,
            "Submitted",
            image_name,
            voice_file,
            student_name,
            datetime.now(),
            is_anonymous_flag
        ))
        db.commit()

        return redirect("/student")

    return render_template("complaint.html")

# ================= ADMIN DASHBOARD =================
@app.route("/admin")
def admin():
    if "role" not in session or session["role"] != "admin":
        return redirect("/login")

    cursor.execute("SELECT * FROM complaints")
    complaints = cursor.fetchall()

    cursor.execute("SELECT id,username,email,role FROM users")
    users = cursor.fetchall()

    return render_template("admin.html",
                           complaints=complaints,
                           users=users)

# ================= RESOLVE =================
@app.route("/resolve/<int:cid>")
def resolve(cid):
    if "role" not in session or session["role"] != "admin":
        return redirect("/login")

    cursor.execute(
        "UPDATE complaints SET status='Resolved', resolved_time=%s WHERE id=%s",
        (datetime.now(), cid)
    )
    db.commit()

    return redirect("/admin")

# ================= MAKE ADMIN =================
@app.route("/make-admin/<int:uid>")
def make_admin(uid):
    if "role" not in session or session["role"] != "admin":
        return redirect("/login")

    cursor.execute("UPDATE users SET role='admin' WHERE id=%s", (uid,))
    db.commit()

    return redirect("/admin")

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)