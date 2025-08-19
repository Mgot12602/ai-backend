// MongoDB initialization script
db = db.getSiblingDB('ai_backend');

// Create users collection with indexes
db.createCollection('users');
db.users.createIndex({ "clerk_id": 1 }, { unique: true });
db.users.createIndex({ "email": 1 }, { unique: true });
db.users.createIndex({ "created_at": 1 });

// Create jobs collection with indexes
db.createCollection('jobs');
db.jobs.createIndex({ "user_id": 1 });
db.jobs.createIndex({ "status": 1 });
db.jobs.createIndex({ "job_type": 1 });
db.jobs.createIndex({ "created_at": 1 });
db.jobs.createIndex({ "user_id": 1, "created_at": -1 });

// Create a user for the application
db.createUser({
  user: "ai_backend_user",
  pwd: "ai_backend_password",
  roles: [
    {
      role: "readWrite",
      db: "ai_backend"
    }
  ]
});

print("Database initialized successfully!");
