# API Documentation

## Project Name

CivicLink

Version 1.0

---

# Authentication APIs

POST /api/auth/register

POST /api/auth/login

POST /api/auth/verify-otp

POST /api/auth/logout

---

# Citizen APIs

GET /api/profile

PUT /api/profile

GET /api/dashboard

---

# Complaint APIs

POST /api/complaints

GET /api/complaints

GET /api/complaints/{id}

PUT /api/complaints/{id}

DELETE /api/complaints/{id}

POST /api/complaints/{id}/images

GET /api/complaints/status

---

# Project APIs

GET /api/projects

GET /api/projects/{id}

POST /api/projects

PUT /api/projects/{id}

---

# Notification APIs

GET /api/notifications

PUT /api/notifications/read

---

# Emergency APIs

GET /api/emergency

POST /api/emergency/request

---

# Admin APIs

GET /api/users

POST /api/users

PUT /api/users

DELETE /api/users

GET /api/reports

---

# AI APIs

POST /api/ai/classify

POST /api/ai/chat

POST /api/ai/image-analysis

---

# End of API Documentation