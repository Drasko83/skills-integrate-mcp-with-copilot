CREATE TABLE IF NOT EXISTS activities (
    name TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    schedule TEXT NOT NULL,
    max_participants INTEGER NOT NULL CHECK (max_participants > 0)
);

CREATE TABLE IF NOT EXISTS enrollments (
    activity_name TEXT NOT NULL,
    email TEXT NOT NULL,
    PRIMARY KEY (activity_name, email),
    FOREIGN KEY (activity_name) REFERENCES activities(name) ON DELETE CASCADE
);