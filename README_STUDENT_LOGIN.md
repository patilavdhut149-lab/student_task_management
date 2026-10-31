# Student Task Manager - Student Login Update

This version adds the requested student workflow:

1. Admin/User logs in.
2. Admin adds a student and creates a student username/password.
3. Admin creates a task.
4. Admin assigns the task to a selected student.
5. A newly assigned task starts with **Pending** status.
6. Student logs in through **Student Login**.
7. Student sees only tasks assigned to that student.
8. Student clicks **Mark Complete** after finishing a task.
9. The same assignment becomes **Complete** in the Admin/User's **Student Tasks** page.

## Important

- The app automatically creates the `student_accounts` table if it does not exist.
- The app automatically adds the `status` column to `student_tasks` if it does not exist.
- Existing task assignments receive the default status `Pending`.
- Student passwords are stored as hashes.

## Student account for an existing student

Open **Students** in the Admin panel and click **Create Login** for that student. Enter a username and password, then use those credentials on the Student Login page.
