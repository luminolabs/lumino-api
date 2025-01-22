# Lumino API - Common SQL Queries

## 1️⃣ Check If a Newly Signed-Up User Has Run a Job
```sql
SELECT u.id, u.email, COUNT(j.id) AS job_count
FROM users u
LEFT JOIN fine_tuning_jobs j ON u.id = j.user_id
WHERE u.created_at >= NOW() - INTERVAL '7 days'
GROUP BY u.id, u.email;
```
**Description:**
- Retrieves newly signed-up users within the last **7 days**.
- Counts the number of jobs they have submitted.
- Helps identify users who signed up but haven't started a job.
- Modify `INTERVAL '7 days'` as needed.

---

## 2️⃣ Find Users Who Signed Up But Haven’t Run a Job
```sql
SELECT u.id, u.email
FROM users u
LEFT JOIN fine_tuning_jobs j ON u.id = j.user_id
WHERE j.id IS NULL
AND u.created_at >= NOW() - INTERVAL '7 days';
```
**Description:**
- Identifies newly signed-up users who **haven’t run any jobs**.
- Helps in outreach to encourage users to start their first training job.

---

## 3️⃣ List All Fine-Tuning Jobs with Status for a Specific User
```sql
SELECT j.id, j.name, j.status, j.created_at, j.updated_at, j.total_epochs, j.current_epoch
FROM fine_tuning_jobs j
JOIN users u ON j.user_id = u.id
WHERE u.email = 'user@example.com'
ORDER BY j.created_at DESC;
```
**Description:**
- Retrieves all jobs for a specific user, including **status and progress**.
- Replace `'user@example.com'` with the actual user email.

---

## 4️⃣ Find Users Who Have Failed Fine-Tuning Jobs
```sql
SELECT u.id, u.email, j.id AS job_id, j.status, j.created_at
FROM fine_tuning_jobs j
JOIN users u ON j.user_id = u.id
WHERE j.status = 'FAILED'
ORDER BY j.created_at DESC;
```
**Description:**
- Retrieves users whose fine-tuning jobs **failed**.
- Useful for diagnosing issues and reaching out with support.

---

## 5️⃣ Get the Most Recent Fine-Tuning Job for Each User
```sql
SELECT DISTINCT ON (j.user_id)
       j.user_id, u.email, j.id AS job_id, j.status, j.created_at
FROM fine_tuning_jobs j
JOIN users u ON j.user_id = u.id
ORDER BY j.user_id, j.created_at DESC;
```
**Description:**
- Fetches the **latest fine-tuning job** for each user.
- Helps track recent activity and engagement.

---

## 6️⃣ Find the Most Active Users (Who Ran the Most Jobs)
```sql
SELECT u.id, u.email, COUNT(j.id) AS total_jobs
FROM users u
JOIN fine_tuning_jobs j ON u.id = j.user_id
GROUP BY u.id, u.email
ORDER BY total_jobs DESC
LIMIT 10;
```
**Description:**
- Identifies the **top 10 most active users** based on job submissions.
- Useful for recognizing power users and potential advocates.

---

## 7️⃣ Get the Most Popular Base Models Used for Fine-Tuning
```sql
SELECT b.name, COUNT(j.id) AS total_jobs
FROM fine_tuning_jobs j
JOIN base_models b ON j.base_model_id = b.id
GROUP BY b.name
ORDER BY total_jobs DESC
LIMIT 5;
```
**Description:**
- Lists the **top 5 most commonly fine-tuned models**.
- Useful for understanding model demand and trends.

---

### ℹ️ **Notes:**
- Ensure you replace placeholders (`'user@example.com'`, `'7 days'`) as needed.
- You can modify these queries to analyze **specific time frames** (e.g., last 30 days).
- Additional status values (`PENDING`, `RUNNING`, `COMPLETED`), you can filter by them in queries.  

