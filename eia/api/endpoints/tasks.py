from fastapi import APIRouter, HTTPException, BackgroundTasks
from celery.result import AsyncResult
from ...tasks import process_all_accounts_task

router = APIRouter()

@router.post("/scan", status_code=202)
def trigger_email_scan():
    """
    Manually triggers the asynchronous task to scan all email accounts.

    This endpoint immediately returns a task ID, which can be used to check
    the status of the task later.
    """
    try:
        # ".delay()" is how you call a Celery task to run in the background.
        task = process_all_accounts_task.delay()
        return {"message": "Email scan task initiated.", "task_id": task.id}
    except Exception as e:
        # This might happen if the broker (Redis) is down.
        raise HTTPException(status_code=500, detail=f"Failed to queue task: {e}")


@router.get("/scan/status/{task_id}")
def get_task_status(task_id: str):
    """
    Checks the status of a background task given its ID.
    """
    task_result = AsyncResult(task_id, app=process_all_accounts_task.app)

    response = {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result if task_result.ready() else None
    }

    if task_result.failed():
        # If the task failed, the result is the exception object.
        response["result"] = str(task_result.result)

    return response