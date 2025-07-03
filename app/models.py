# app/student/models.py

from sqlalchemy import Integer, String, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base
from sqlalchemy import Table, Column, ForeignKey, BigInteger
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional
from sqlalchemy.ext.declarative import declarative_base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=True)
    surname: Mapped[str] = mapped_column(String(50), nullable=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    platform_id: Mapped[int] = mapped_column(BigInteger)
    user_type: Mapped[str] = mapped_column(String(50), nullable=True)


class Teacher(Base):
    __tablename__ = "teacher"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform_id: Mapped[int] = mapped_column(BigInteger)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


parent_student_association = Table(
    "parent_student_association",
    Base.metadata,
    Column("parent_id", ForeignKey("parent.id"), primary_key=True),
    Column("student_id", ForeignKey("student.id"), primary_key=True),
)


class Parent(Base):
    __tablename__ = "parent"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform_id: Mapped[int] = mapped_column(BigInteger)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # Relationship to Student
    students: Mapped[list["Student"]] = relationship(
        "Student",
        secondary=parent_student_association,
        back_populates="parents",
        order_by="Student.id",
    )


class Student(Base):
    __tablename__ = "student"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform_id: Mapped[int] = mapped_column(BigInteger)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(50), nullable=True)
    surname: Mapped[str] = mapped_column(String(50), nullable=True)
    # Relationship to Parent
    parents: Mapped[list["Parent"]] = relationship(
        "Parent",
        secondary=parent_student_association,
        back_populates="students"
    )
