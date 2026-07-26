# Database Design

## Project Name

CivicLink – Smart Municipal Governance Platform

Version: 1.0

---

# 1. Database Overview

CivicLink uses PostgreSQL as the primary relational database.

The database is designed to support:

- Citizens
- Nagar Sevaks
- Municipal Officers
- Engineers
- Contractors
- Departments
- Wards
- Municipal Corporations
- Complaints
- Government Projects
- Emergency Services
- Notifications
- Assets

---

# 2. Database Type

- Relational Database
- SQL Database
- ACID Compliant
- Cloud Ready

Database Engine:

PostgreSQL

---

# 3. Main Tables

## User

Stores all registered users.

Columns

- id
- full_name
- mobile
- email
- password_hash
- role_id
- ward_id
- created_at

---

## Role

Stores user roles.

Columns

- id
- role_name

Values

- Citizen
- Nagar Sevak
- Officer
- Engineer
- Contractor
- Admin

---

## Ward

Stores ward information.

Columns

- id
- ward_name
- municipal_id

---

## Municipal Corporation

Columns

- id
- corporation_name
- city
- state

---

## Department

Columns

- id
- department_name

Examples

- Water
- Road
- Street Light
- Drainage
- Sanitation
- Health
- Garden

---

## Complaint

Columns

- id
- citizen_id
- department_id
- ward_id
- title
- description
- status
- priority
- latitude
- longitude
- created_at

---

## Complaint Images

Columns

- id
- complaint_id
- image_url

---

## Complaint Status History

Columns

- id
- complaint_id
- status
- updated_by
- updated_at

---

## Government Project

Columns

- id
- project_name
- department_id
- budget
- start_date
- end_date
- completion_percentage

---

## Project Progress

Columns

- id
- project_id
- description
- image_url
- uploaded_at

---

## Notification

Columns

- id
- user_id
- title
- message
- is_read

---

## Feedback

Columns

- id
- complaint_id
- citizen_id
- rating
- review

---

## Emergency Contacts

Columns

- id
- department
- phone_number

---

## Public Assets

Columns

- id
- asset_type
- ward_id
- location
- status

Examples

- Street Light
- Road
- Drain
- Dustbin
- Water Tank
- Park

---

## Audit Log

Columns

- id
- user_id
- action
- created_at

---

# 4. Relationships

One Role → Many Users

One Ward → Many Users

One Ward → Many Complaints

One Complaint → Many Images

One Complaint → Many Status Updates

One Department → Many Complaints

One Department → Many Projects

One Project → Many Progress Updates

One Citizen → Many Complaints

One Complaint → One Feedback

---

# 5. Database Goals

- High Performance
- Secure
- Scalable
- Easy Backup
- Cloud Ready
- ACID Compliance

---

# End of Database Design