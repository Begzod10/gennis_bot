from sqlalchemy import text
from app.db import SessionLocal

def check():
    with SessionLocal() as session:
        res = session.execute(text('SELECT count(*) FROM parent'))
        print(f'Parents: {res.scalar()}')
        res = session.execute(text('SELECT count(*) FROM student'))
        print(f'Students (bot): {res.scalar()}')
        res = session.execute(text('SELECT count(*) FROM parent_student_association'))
        print(f'Associations: {res.scalar()}')

if __name__ == "__main__":
    check()
