from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    persons = relationship("Person", back_populates="project", cascade="all, delete-orphan")


class Person(Base):
    __tablename__ = "persons"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    nome = Column(String, default="")
    cognome = Column(String, default="")
    codice_fiscale = Column(String, default="")
    indirizzo_domicilio = Column(String, default="")
    indirizzo_residenza = Column(String, default="")
    data_nascita = Column(String, default="")
    comune_nascita = Column(String, default="")
    provincia_nascita = Column(String, default="")
    sesso = Column(String, default="")
    numero_documento = Column(String, default="")
    ente_rilascio = Column(String, default="")
    data_rilascio = Column(String, default="")
    data_scadenza = Column(String, default="")
    titolo_studio_piu_recente = Column(String, default="")
    data_conseguimento_titolo = Column(String, default="")
    situazione_occupazionale = Column(String, default="")
    privacy_ok = Column(Boolean, default=False)
    cv_firmato = Column(Boolean, default=False)
    data_cv = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="persons")