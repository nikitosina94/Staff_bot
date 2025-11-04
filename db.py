import os
from datetime import date
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, extract
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    position = Column(String, nullable=True)
    attendances = relationship("Attendance", back_populates="employee", cascade="all, delete-orphan")


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    date = Column(Date, default=date.today)
    employee = relationship("Employee", back_populates="attendances")


def init_db():
    Base.metadata.create_all(engine)


def add_employee(name, position=None):
    session = Session()
    emp = Employee(name=name, position=position)
    session.add(emp)
    session.commit()
    session.close()


def delete_employee(emp_id):
    session = Session()
    emp = session.query(Employee).get(emp_id)
    if emp:
        session.delete(emp)
        session.commit()
    session.close()


def get_employees():
    session = Session()
    employees = session.query(Employee).all()
    session.close()
    return employees


def mark_attendance(emp_id, day=None):
    session = Session()
    if not day:
        day = date.today()
    attendance = Attendance(employee_id=emp_id, date=day)
    session.add(attendance)
    session.commit()
    session.close()


def get_attendance_report(month=None, year=None):
    session = Session()
    employees = session.query(Employee).all()
    report = []
    for emp in employees:
        query = session.query(Attendance).filter(Attendance.employee_id == emp.id)
        if month:
            query = query.filter(extract('month', Attendance.date) == month)
        if year:
            query = query.filter(extract('year', Attendance.date) == year)
        days = [a.date.strftime("%Y-%m-%d") for a in query.all()]
        report.append({
            "name": emp.name,
            "position": emp.position,
            "days": days,
            "total": len(days)
        })
    session.close()
    return report


def get_employee_history(emp_id, month=None, year=None):
    session = Session()
    emp = session.query(Employee).get(emp_id)
    if not emp:
        session.close()
        return None
    query = session.query(Attendance).filter(Attendance.employee_id == emp_id)
    if month:
        query = query.filter(extract('month', Attendance.date) == month)
    if year:
        query = query.filter(extract('year', Attendance.date) == year)
    days = [a.date.strftime("%Y-%m-%d") for a in query.all()]
    session.close()
    return {"name": emp.name, "position": emp.position, "days": days, "total": len(days)}
