import logging
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..limiter import limiter
from ..models import SurveyResponse

router = APIRouter()
logger = logging.getLogger("boxoffice")

# The questionnaire is free to change without touching this file, so the payload is
# accepted as an open key/value bag. These caps are the only thing standing between
# an open POST endpoint and someone using the answers column as free storage.
MAX_FIELDS = 100
MAX_KEY_LEN = 100
MAX_VALUE_LEN = 2000


class SurveySubmission(BaseModel):
    answers: Dict[str, str]


@router.post("/survey")
@limiter.limit("5/minute")
def submit_survey(request: Request, req: SurveySubmission, db: Session = Depends(get_db)):
    if not req.answers:
        raise HTTPException(status_code=400, detail="Empty submission")
    if len(req.answers) > MAX_FIELDS:
        raise HTTPException(status_code=400, detail="Too many fields")

    answers = {k[:MAX_KEY_LEN]: v[:MAX_VALUE_LEN] for k, v in req.answers.items()}
    db.add(SurveyResponse(answers=answers))
    db.commit()
    return {"success": True}
