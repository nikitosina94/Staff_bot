import os
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, func
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import date

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()

class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    position = Column(String, nullable=True)
    attendance = relationship("Attendance", back_populates="employee")

class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    date = Column(Date, default=date.today)
    employee = relationship("Employee", back_populates="attendance")

Base.metadata.create_all(engine)

# Функции
def add_employee(name, position=None):
    session = Session()
    emp = Employee(name=name, position=position)
    session.add(emp)
    session.commit()
    session.close()

def list_employees():
    session = Session()
    employees = session.query(Employee).all()
    result = [{"id": e.id, "name": e.name} for e in employees]
    session.close()
    return result

def mark_attendance(emp_id, mark_date=None):
    session = Session()
    if mark_date is None:
        mark_date = date.today()
    attendance = Attendance(employee_id=emp_id, date=mark_date)
    session.add(attendance)
    session.commit()
    session.close()

def get_attendance_report():
    session = Session()
    report = ""
    employees = session.query(Employee).all()
    for emp in employees:
        dates = [a.date.strftime("%Y-%m-%d") for a in emp.attendance]
        report += f"{emp.name} ({emp.position or '-'})\nПрисутствие: {', '.join(dates)}\nВсего смен: {len(dates)}\n\n"
    session.close()
    return report or "Нет данных."
