import os
import shutil
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Project, Person
from auth import create_default_user, login_action, logout_action, require_login, get_current_user
from ocr import extract_text
from ai_extraction import extract_fields_with_ai

app = FastAPI(title="Controllo Documenti e CRM")
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "supersecretkey"))

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Initialize DB
Base.metadata.create_all(bind=engine)
with next(get_db()) as db:
    create_default_user(db)


def save_upload(file: UploadFile, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return destination


def build_alerts(data: dict) -> List[str]:
    alerts: List[str] = []
    if not data.get("indirizzo_domicilio"):
        alerts.append("Manca l'indirizzo di domicilio nel CV")
    if not data.get("indirizzo_residenza"):
        alerts.append("Manca l'indirizzo di residenza nel CV")
    if not data.get("privacy_clause_present"):
        alerts.append("Manca la clausola di trattamento dei dati personali nel CV")
    if not data.get("nome"):
        alerts.append("Manca il nome nel CV")
    if not data.get("cognome"):
        alerts.append("Manca il cognome nel CV")
    titolo = data.get("titolo_studio_piu_recente", {})
    if not titolo.get("titolo"):
        alerts.append("Manca il titolo di studio più recente nel CV")
    if not titolo.get("data_conseguimento"):
        alerts.append("Manca la data di conseguimento del titolo nel CV")
    if not data.get("situazione_occupazionale"):
        alerts.append("Manca la situazione occupazionale nel CV")
    if not data.get("firma_presente"):
        alerts.append("Il CV non risulta firmato")
    if not data.get("data_cv"):
        alerts.append("Il CV non risulta datato")
    return alerts


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/progetti", status_code=303)
    return RedirectResponse(url="/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    success = login_action(request, db, username, password)
    if success:
        return RedirectResponse(url="/progetto", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Credenziali non valide"})


@app.get("/logout")
async def logout(request: Request):
    logout_action(request)
    return RedirectResponse(url="/login", status_code=303)


@app.get("/progetto", response_class=HTMLResponse)
async def select_project(request: Request, db: Session = Depends(get_db)):
    if require_login(request):
        return require_login(request)
    current_project_id = request.session.get("project_id")
    project = None
    if current_project_id:
        project = db.query(Project).filter_by(id=current_project_id).first()
    return templates.TemplateResponse("select_project.html", {"request": request, "project": project})


@app.post("/progetto")
async def set_project(request: Request, project_name: str = Form(...), db: Session = Depends(get_db)):
    if require_login(request):
        return require_login(request)
    project = db.query(Project).filter_by(name=project_name.strip()).first()
    if not project:
        project = Project(name=project_name.strip())
        db.add(project)
        db.commit()
        db.refresh(project)
    request.session["project_id"] = project.id
    return RedirectResponse(url="/upload", status_code=303)


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request, db: Session = Depends(get_db)):
    if require_login(request):
        return require_login(request)
    project_id = request.session.get("project_id")
    project = db.query(Project).filter_by(id=project_id).first() if project_id else None
    if not project:
        return RedirectResponse(url="/progetto", status_code=303)
    return templates.TemplateResponse("upload_documents.html", {"request": request, "project": project})


@app.post("/process", response_class=HTMLResponse)
async def process_documents(
    request: Request,
    cv: UploadFile = File(...),
    documento_identita: UploadFile = File(...),
    tessera_sanitaria: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if require_login(request):
        return require_login(request)
    project_id = request.session.get("project_id")
    project = db.query(Project).filter_by(id=project_id).first() if project_id else None
    if not project:
        return RedirectResponse(url="/progetto", status_code=303)

    cv_path = save_upload(cv, UPLOAD_DIR / f"cv_{cv.filename}")
    doc_path = save_upload(documento_identita, UPLOAD_DIR / f"doc_{documento_identita.filename}")
    tess_path = save_upload(tessera_sanitaria, UPLOAD_DIR / f"tess_{tessera_sanitaria.filename}")

    testo_cv, _ = extract_text(str(cv_path))
    testo_doc, _ = extract_text(str(doc_path))
    testo_tess, _ = extract_text(str(tess_path))

    data = extract_fields_with_ai(testo_cv, testo_doc, testo_tess)
    alerts = build_alerts(data)

    person = Person(
        project_id=project.id,
        nome=data.get("nome", ""),
        cognome=data.get("cognome", ""),
        codice_fiscale=data.get("codice_fiscale", ""),
        indirizzo_domicilio=data.get("indirizzo_domicilio", ""),
        indirizzo_residenza=data.get("indirizzo_residenza", ""),
        data_nascita=data.get("data_nascita", ""),
        comune_nascita=data.get("comune_nascita", ""),
        provincia_nascita=data.get("provincia_nascita", ""),
        sesso=data.get("sesso", ""),
        numero_documento=data.get("numero_documento", ""),
        ente_rilascio=data.get("ente_rilascio", ""),
        data_rilascio=data.get("data_rilascio", ""),
        data_scadenza=data.get("data_scadenza", ""),
        titolo_studio_piu_recente=data.get("titolo_studio_piu_recente", {}).get("titolo", ""),
        data_conseguimento_titolo=data.get("titolo_studio_piu_recente", {}).get("data_conseguimento", ""),
        situazione_occupazionale=data.get("situazione_occupazionale", ""),
        privacy_ok=bool(data.get("privacy_clause_present")),
        cv_firmato=bool(data.get("firma_presente")),
        data_cv=data.get("data_cv", ""),
    )
    db.add(person)
    db.commit()
    db.refresh(person)

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "project": project,
            "data": data,
            "alerts": alerts,
        },
    )


@app.get("/progetti", response_class=HTMLResponse)
async def list_projects(request: Request, db: Session = Depends(get_db)):
    if require_login(request):
        return require_login(request)
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return templates.TemplateResponse("projects_list.html", {"request": request, "projects": projects})


@app.get("/progetti/{project_id}", response_class=HTMLResponse)
async def project_detail(request: Request, project_id: int, db: Session = Depends(get_db)):
    if require_login(request):
        return require_login(request)
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        return RedirectResponse(url="/progetti", status_code=303)
    persons = db.query(Person).filter_by(project_id=project.id).all()
    return templates.TemplateResponse(
        "project_detail.html", {"request": request, "project": project, "persons": persons}
    )


@app.get("/persone/{person_id}", response_class=HTMLResponse)
async def person_detail(request: Request, person_id: int, db: Session = Depends(get_db)):
    if require_login(request):
        return require_login(request)
    person = db.query(Person).filter_by(id=person_id).first()
    if not person:
        return RedirectResponse(url="/progetti", status_code=303)
    project = db.query(Project).filter_by(id=person.project_id).first()
    return templates.TemplateResponse(
        "person_detail.html", {"request": request, "project": project, "person": person}
    )