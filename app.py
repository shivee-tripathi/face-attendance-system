from multiprocessing.dummy import connection

from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
import cv2
import face_recognition
import pickle
import base64
import numpy as np
from datetime import datetime, date, timedelta

app = Flask(__name__)


app.secret_key = "face_attendance_secret_key"

DATABASE = "database/attendance.db"
FACE_DATA = "face_data"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.path.join(
    BASE_DIR, "database", "attendance.db"
)

FACE_DATA = os.path.join(BASE_DIR, "face_data")


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    os.makedirs("database", exist_ok=True)
    os.makedirs(FACE_DATA, exist_ok=True)

    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_no TEXT NOT NULL UNIQUE,
            face_encoding TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        UNIQUE(student_id, date),
        FOREIGN KEY(student_id) REFERENCES students(id)
    )
""")

    
    

    connection.commit()
    connection.close()




@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":
            session["logged_in"] = True
            return redirect(url_for("dashboard"))

        return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")



@app.route("/dashboard")
def dashboard():

    if not session.get("logged_in"):
        return redirect(url_for("login"))

    return render_template("dashboard.html")


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


@app.route("/add-student", methods=["GET", "POST"])
def add():

    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":

        name = request.form["name"]
        roll_no = request.form["roll_no"]
        image_data = request.form.get("face_image")

        # Check whether image was captured
        if not image_data:
            return render_template(
                "add.html",
                error="Please capture your face first."
            )

        connection = get_db_connection()

        try:

            # Check duplicate roll number
            existing_student = connection.execute(
                "SELECT * FROM students WHERE roll_no = ?",
                (roll_no,)
            ).fetchone()

            if existing_student:
                connection.close()

                return render_template(
                    "add.html",
                    error="Roll number already exists."
                )

            # --------------------------------
            # Convert browser image to OpenCV image
            # --------------------------------

            image_bytes = base64.b64decode(
                image_data.split(",")[1]
            )

            image_array = np.frombuffer(
                image_bytes,
                dtype=np.uint8
            )

            frame = cv2.imdecode(
                image_array,
                cv2.IMREAD_COLOR
            )

            if frame is None:
                connection.close()

                return render_template(
                    "add.html",
                    error="Could not process captured image."
                )

            # --------------------------------
            # Convert BGR to RGB
            # --------------------------------

            rgb_frame = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            # --------------------------------
            # Detect face
            # --------------------------------

            face_locations = face_recognition.face_locations(
                rgb_frame
            )

            if len(face_locations) == 0:

                connection.close()

                return render_template(
                    "add.html",
                    error="No face detected. Please capture your face clearly."
                )

            if len(face_locations) > 1:

                connection.close()

                return render_template(
                    "add.html",
                    error="Multiple faces detected. Please keep only one person in the camera."
                )

            # --------------------------------
            # Generate face encoding
            # --------------------------------

            face_encodings = face_recognition.face_encodings(
                rgb_frame,
                face_locations
            )

            if not face_encodings:

                connection.close()

                return render_template(
                    "add.html",
                    error="Could not generate face encoding."
                )

            face_encoding = face_encodings[0]
            
            # Check for duplicate face
            all_students = connection.execute(
                """
                SELECT name, roll_no, face_encoding
                FROM students
                WHERE face_encoding IS NOT NULL
                """
            ).fetchall()

            for student in all_students:

                saved_encoding = pickle.loads(
                    bytes.fromhex(student["face_encoding"])
                )

                saved_encoding = np.array(saved_encoding)

                distance = face_recognition.face_distance(
                    [saved_encoding],
                    face_encoding
                )[0]

                if distance < 0.50:
                    connection.close()

                    return render_template(
                        "add.html",
                        error=(
                            "This face is already registered for "
                            + student["name"]
                            + " (Roll No: "
                            + student["roll_no"]
                            + "). Please check the existing record."
                        )
                    )

            # Convert encoding to list
            encoding_list = face_encoding.tolist()

            # --------------------------------
            # Save student in database
            # --------------------------------

            connection.execute(
                """
                INSERT INTO students
                (name, roll_no, face_encoding)
                VALUES (?, ?, ?)
                """,
                (
                    name,
                    roll_no,
                    pickle.dumps(encoding_list).hex()
                )
            )

            connection.commit()
            connection.close()

            print("Student registered successfully!")
            print("Name:", name)
            print("Roll No:", roll_no)
            print("Face encoding generated:", len(encoding_list))

            return redirect(url_for("dashboard"))

        except Exception as error:

            connection.close()

            print("Error:", error)

            return render_template(
                "add.html",
                error="Something went wrong while registering the student."
            )

    return render_template("add.html")


@app.route("/attendence", methods=["GET", "POST"])
def attendence():

    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":

        image_data = request.form.get("face_image")

        if not image_data:
            return render_template(
                "attendence.html",
                error="No face image received."
            )

        connection = get_db_connection()

        try:
            # Convert captured image
            image_bytes = base64.b64decode(
                image_data.split(",")[1]
            )

            image_array = np.frombuffer(
                image_bytes,
                dtype=np.uint8
            )

            frame = cv2.imdecode(
                image_array,
                cv2.IMREAD_COLOR
            )

            if frame is None:
                return render_template(
                    "attendence.html",
                    error="Could not process the captured image."
                )

            rgb_frame = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            # Detect face
            face_locations = face_recognition.face_locations(
                rgb_frame
            )

            if len(face_locations) == 0:
                return render_template(
                    "attendence.html",
                    error="No face detected. Please try again."
                )

            if len(face_locations) > 1:
                return render_template(
                    "attendence.html",
                    error="Multiple faces detected. Only one person should be in the camera."
                )

            # Generate encoding
            encodings = face_recognition.face_encodings(
                rgb_frame,
                face_locations
            )

            if not encodings:
                return render_template(
                    "attendence.html",
                    error="Could not recognize the face. Try again."
                )

            captured_encoding = encodings[0]

            # Load registered students
            students = connection.execute(
                """
                SELECT id, name, roll_no, face_encoding
                FROM students
                WHERE face_encoding IS NOT NULL
                """
            ).fetchall()

            if not students:
                return render_template(
                    "attendence.html",
                    error="No students are registered yet."
                )

            # Compare captured face with saved faces
            known_encodings = []
            valid_students = []

            for student in students:
                saved_encoding = np.array(
                    pickle.loads(
                        bytes.fromhex(student["face_encoding"])
                    )
                )

                if saved_encoding.shape == (128,):
                    known_encodings.append(saved_encoding)
                    valid_students.append(student)

            if not known_encodings:
                return render_template(
                    "attendence.html",
                    error="No valid registered face data found."
                )

            distances = face_recognition.face_distance(
                known_encodings,
                captured_encoding
            )

            best_index = int(np.argmin(distances))
            best_distance = float(distances[best_index])

            # Initial matching threshold; needs real-world testing
            if best_distance >= 0.50:
                return render_template(
                    "attendence.html",
                    error="Face not recognized. Student is not registered."
                )

            matched_student = valid_students[best_index]

            # Get today's date and current time
            now = datetime.now().astimezone()
            today = now.date().isoformat()
            current_time = now.strftime("%H:%M:%S")

            # Check whether attendance is already marked
            existing_attendance = connection.execute(
                """
                SELECT id FROM attendance
                WHERE student_id = ? AND date = ?
                """,
                (matched_student["id"], today)
            ).fetchone()

            if existing_attendance:
                return render_template(
                    "attendence.html",
                    error=(
                        "Attendance already marked today for "
                        + matched_student["name"]
                        + " (Roll No: "
                        + matched_student["roll_no"]
                        + ")."
                    )
                )

            # Save attendance
            connection.execute(
                """
                INSERT INTO attendance
                (student_id, date, time)
                VALUES (?, ?, ?)
                """,
                (
                    matched_student["id"],
                    today,
                    current_time
                )
            )

            connection.commit()

            print("DATABASE USED:", os.path.abspath(DATABASE))
            print("ATTENDANCE DATE:", today)

            saved_row = connection.execute(
            "SELECT student_id, date, time FROM attendance WHERE student_id=? AND date=?",
            (matched_student["id"], today)
            ).fetchone()

            print("SAVED ROW:", dict(saved_row) if saved_row else None)

            return render_template(
                "attendence.html",
                message=(
                    "Attendance marked successfully! Student: "
                    + matched_student["name"]
                    + " | Roll No: "
                    + matched_student["roll_no"]
                    + " | Date: "
                    + today
                    + " | Time: "
                    + current_time
                )
            )

        except Exception as error:
            print("Attendance error:", error)
            connection.rollback()

            return render_template(
                "attendence.html",
                error="An error occurred while processing attendance. Check the terminal."
            )

        finally:
            connection.close()

    return render_template("attendence.html")




@app.route("/view-attendance", methods=["GET"])
def view():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    
    import calendar

    import calendar

    today = datetime.now().astimezone().date()
    selected_filter = request.args.get("filter", "today")
    selected_date = request.args.get("date", today.isoformat())
    selected_month = request.args.get("month", today.strftime("%Y-%m"))
    student_search = request.args.get("student", "").strip()

    start_date = today
    end_date = today

    # Weekly: Monday to Friday only
    if selected_filter == "weekly":
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=4)

    # Monthly report
    elif selected_filter == "monthly":
        try:
            year, month = map(int, selected_month.split("-"))
            start_date = date(year, month, 1)

            last_day = calendar.monthrange(year, month)[1]
            end_date = date(year, month, last_day)

            if start_date > today:
                selected_month = today.strftime("%Y-%m")
                start_date = today.replace(day=1)
                end_date = today

        except (ValueError, TypeError):
            selected_month = today.strftime("%Y-%m")
            start_date = today.replace(day=1)
            end_date = today

    # Specific date
    elif selected_filter == "specific":
        try:
            chosen_date = date.fromisoformat(selected_date)
            if chosen_date > today:
                chosen_date = today

            selected_date = chosen_date.isoformat()
            start_date = chosen_date
            end_date = chosen_date

        except ValueError:
            selected_date = today.isoformat()
            start_date = today
            end_date = today

    # Never include future dates
    if end_date > today:
        end_date = today

    # Generate Monday-Friday dates only
    working_dates = []
    current_date = start_date

    while current_date <= end_date:
        if current_date.weekday() < 5:
            working_dates.append(current_date.isoformat())
        current_date += timedelta(days=1)

    connection = get_db_connection()

    try:
        query = """
            SELECT id, name, roll_no, created_at
            FROM students
            WHERE 1 = 1
        """
        parameters = []

        if student_search:
            query += """
                AND (name LIKE ? OR roll_no LIKE ?)
            """
            search_value = "%" + student_search + "%"
            parameters.extend([search_value, search_value])

        query += " ORDER BY name COLLATE NOCASE ASC"

        students = connection.execute(
            query, parameters
        ).fetchall()

        attendance_rows = connection.execute(
            """
            SELECT student_id, date, time
            FROM attendance
            WHERE date BETWEEN ? AND ?
            """,
            [start_date.isoformat(), end_date.isoformat()]
        ).fetchall()

        attendance_map = {
            (row["student_id"], row["date"]): row["time"]
            for row in attendance_rows
        }

        matrix_records = []

        for student in students:
            days = []
            present_count = 0
            absent_count = 0

            for working_date in working_dates:
                # Do not count days before the student registered
                registration_date = (
                    student["created_at"][:10]
                    if student["created_at"]
                    else working_date
                )

                if working_date < registration_date:
                    status = "-"
                    time = None
                elif (student["id"], working_date) in attendance_map:
                    status = "P"
                    time = attendance_map[
                        (student["id"], working_date)
                    ]
                    present_count += 1
                else:
                    status = "A"
                    time = None
                    absent_count += 1

                days.append({
                    "date": working_date,
                    "status": status,
                    "time": time
                })

            matrix_records.append({
                "id": student["id"],
                "name": student["name"],
                "roll_no": student["roll_no"],
                "days": days,
                "present_count": present_count,
                "absent_count": absent_count
            })

        total_students = len(matrix_records)
        present_count = sum(
            record["present_count"] for record in matrix_records
        )
        absent_count = sum(
            record["absent_count"] for record in matrix_records
        )

        # Keep today's/specific-date report compatible with the current table
        records = []

        for record in matrix_records:
            present_day = next(
                (day for day in record["days"]
                 if day["status"] == "P"),
                None
            )

            records.append({
                "id": record["id"],
                "name": record["name"],
                "roll_no": record["roll_no"],
                "date": (
                    present_day["date"]
                    if present_day else None
                ),
                "time": (
                    present_day["time"]
                    if present_day else None
                )
            })

        return render_template(
            "view.html",
            records=records,
            matrix_records=matrix_records,
            working_dates=working_dates,
            selected_filter=selected_filter,
            selected_date=selected_date,
            selected_month=selected_month,
            student_search=student_search,
            present_count=present_count,
            absent_count=absent_count,
            total_students=total_students,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )

    except Exception as error:
        print("View attendance error:", error)
        return "Unable to load attendance records. Check the terminal."

    finally:
        connection.close()

        
import csv
from flask import make_response


@app.route("/export-attendance")
def export_attendance():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    from datetime import date
    import csv
    import io
    from flask import make_response

    selected_date = request.args.get(
        "date", date.today().isoformat()
    )

    connection = get_db_connection()

    try:
        records = connection.execute(
            """
            SELECT
                students.roll_no,
                students.name,
                attendance.date,
                attendance.time
            FROM students
            LEFT JOIN attendance
                ON students.id = attendance.student_id
                AND attendance.date = ?
            ORDER BY students.name COLLATE NOCASE
            """,
            [selected_date]
        ).fetchall()

        # Create CSV content in memory
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Roll Number",
            "Student Name",
            "Date",
            "Time",
            "Status"
        ])

        for record in records:
            status = "Present" if record["date"] else "Absent"

            writer.writerow([
                record["roll_no"],
                record["name"],
                record["date"] or selected_date,
                record["time"] or "-",
                status
            ])

        response = make_response("\ufeff" + output.getvalue())
        response.headers["Content-Disposition"] = (
            f"attachment; filename=attendance_{selected_date}.csv"
        )
        response.headers["Content-Type"] = (
            "text/csv; charset=utf-8"
        )

        return response

    except Exception as error:
        print("Export error:", repr(error))
        return "Unable to export attendance. Check the terminal for the error."

    finally:
        connection.close()

        
@app.route("/delete", methods=["GET", "POST"])
def delete():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    connection = get_db_connection()
    message = ""

    try:
        if request.method == "POST":
            roll_no = request.form.get("roll_no", "").strip()

            if not roll_no:
                message = "Please enter a roll number."
            else:
                student = connection.execute(
                    "SELECT id, name FROM students WHERE roll_no = ?",
                    (roll_no,)
                ).fetchone()

                if student:
                    # Delete attendance records first
                    connection.execute(
                        "DELETE FROM attendance WHERE student_id = ?",
                        (student["id"],)
                    )

                    # Then delete the student
                    connection.execute(
                        "DELETE FROM students WHERE id = ?",
                        (student["id"],)
                    )

                    connection.commit()
                    message = (
                        f"Student {student['name']} deleted successfully."
                    )
                else:
                    message = "No student found with this roll number."

        students = connection.execute(
            "SELECT name, roll_no FROM students ORDER BY name"
        ).fetchall()

        return render_template(
            "delete.html",
            students=students,
            message=message
        )

    except Exception as error:
        connection.rollback()
        print("Delete student error:", error)
        return "Unable to delete student. Check the terminal."

    finally:
        connection.close()



        
@app.route("/detect-face", methods=["POST"])
def detect_face():
    if not session.get("logged_in"):
        return {"success": False, "message": "Please login again."}, 401

    try:
        image_data = request.json.get("image", "")

        if "," in image_data:
            image_data = image_data.split(",", 1)[1]

        image_bytes = base64.b64decode(image_data)
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if frame is None:
            return {"success": False, "faces": []}, 400

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb_frame)

        faces = []

        for top, right, bottom, left in locations:
            faces.append({
                "top": top,
                "right": right,
                "bottom": bottom,
                "left": left
            })

        return {
            "success": True,
            "faces": faces
        }

    except Exception as error:
        print("Face detection error:", error)
        return {"success": False, "faces": []}, 500





if __name__ == "__main__":
    init_database()
    app.run(debug=True)