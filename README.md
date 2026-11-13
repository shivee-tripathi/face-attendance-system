# Face Recognition Based Attendance Management System

A web-based attendance management system that uses face recognition technology to identify registered students and mark their attendance.

## About the Project

This project is developed as a college macro project. It aims to simplify the traditional attendance process using face recognition.

An administrator can register students, mark attendance through face recognition, view attendance records, and manage student information.

## Features

- Admin Login System
- Student Registration
- Face Recognition Based Attendance
- Automatic Attendance Date and Time Recording
- Duplicate Attendance Prevention
- View Attendance Records
- Attendance Filtering
- CSV Attendance Export
- Delete Student Records

## Technologies Used

- **Programming Language:** Python
- **Backend:** Flask
- **Computer Vision:** OpenCV, Face Recognition
- **Database:** SQLite
- **Frontend:** HTML, CSS, JavaScript

## Project Structure

```text
face-attendance-system/
│
├── app.py
├── database/
├── face_data/
├── static/
│   └── css/
├── templates/
├── .gitignore
└── README.md
```

*Note: The database and face data folders are created locally and are not included in this public repository.*

## How It Works

1. The administrator logs into the system.
2. Student details and face data are registered.
3. The system captures a face through the camera.
4. The captured face is compared with registered face data.
5. If a match is found, attendance is recorded with the date and time.
6. The administrator can view and manage attendance records.

## Future Improvements

- Liveness Detection to reduce photo-based attendance fraud.
- Improved face recognition accuracy.
- Student Login and Attendance Dashboard.
- Deployment for real-world use.

## Project Status

This is an academic prototype developed for learning and demonstration purposes. It is not yet a production-ready attendance system.

## Author

**Shivee Tripathi**

GitHub: [shivee-tripathi](https://github.com/shivee-tripathi)

## Acknowledgement

Developed as a college macro project with **Shelly Narwariya**.