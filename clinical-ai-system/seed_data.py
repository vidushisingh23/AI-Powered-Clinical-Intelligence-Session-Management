from db import get_db

db = get_db()
cur = db.cursor()

# Insert doctor
'''
cur.execute("""
INSERT INTO doctors (name, email)
VALUES (?, ?)
""", ("Primary Doctor", "sanjeevrptt@gmail.com"))
'''
# doctor_id = cur.lastrowid


# ✅ Delete patient safely
cur.execute("DELETE FROM patients WHERE patient_id = ?", (2,))

db.commit()
db.close()

print("Patient deleted successfully ✅")

'''
# Insert patient linked to doctor
cur.execute("""
FROM patients (name, email, assigned_doctor)
DELETE 
VALUES (?, ?, ?)
""", ("Vidushi Singh", "vidssspu@gmail.com", doctor_id))

db.commit()
db.close()
'''
print("deleted")
