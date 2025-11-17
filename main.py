import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Project

app = FastAPI(title="ÆTHER API", description="Backend for ÆTHER interactive portfolio")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "ÆTHER backend is running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from ÆTHER API"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = getattr(db, 'name', None) or "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    return response

# Utility to convert MongoDB documents to serializable dicts
class ProjectOut(BaseModel):
    id: str
    title: str
    summary: str
    description: Optional[str] = None
    tags: List[str] = []
    year: Optional[int] = None
    featured: bool = False
    cover_image: Optional[str] = None
    demo_url: Optional[str] = None
    media_url: Optional[str] = None

    class Config:
        orm_mode = True


@app.get("/api/projects", response_model=List[ProjectOut])
def list_projects(featured: Optional[bool] = None, limit: int = 12):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    filter_dict = {}
    if featured is not None:
        filter_dict["featured"] = featured

    docs = get_documents("project", filter_dict, limit)
    out: List[ProjectOut] = []
    for d in docs:
        d_id = str(d.get("_id")) if d.get("_id") else None
        d.pop("_id", None)
        out.append(ProjectOut(id=d_id, **d))
    return out


@app.post("/api/projects", status_code=201)
def create_project(project: Project):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    try:
        inserted_id = create_document("project", project)
        return {"id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    try:
        doc = db["project"].find_one({"_id": ObjectId(project_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Project not found")
        doc_id = str(doc.pop("_id"))
        return ProjectOut(id=doc_id, **doc)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
