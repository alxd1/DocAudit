from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from utils.templates import templates

router = APIRouter(tags=['General'])

@router.get("/")
async def root(request: Request):
    return RedirectResponse(url="/homepage")

@router.get("/homepage")
async def homepage(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="homepage/homepage.html"
    )