import time
from pathlib import Path

from app.db.database import SessionLocal
from app.ingestion.service import ingest_document
from app.agent.runner import run_incremental_agent


WATCHED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def process_new_file(
    file_path: str,
    existing_document_ids: list[int],
    rules: list[str] | None = None,
) -> dict:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    if path.suffix.lower() not in WATCHED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {path.suffix}"
        )

    db = SessionLocal()

    try:
        document = ingest_document(
            db=db,
            file_path=str(path),
            filename=path.name,
        )

        new_document_id = document.id

    finally:
        db.close()

    return run_incremental_agent(
        existing_document_ids=existing_document_ids,
        new_document_id=new_document_id,
        rules=rules or [],
    )


def watch_folder(
    folder: str,
    existing_document_ids: list[int],
    rules: list[str] | None = None,
    poll_seconds: float = 2.0,
):
    watch_path = Path(folder)

    watch_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    processed: set[str] = set()

    print(
        f"Watching folder: {watch_path.resolve()}"
    )

    while True:
        for path in watch_path.iterdir():
            if not path.is_file():
                continue

            if path.suffix.lower() not in WATCHED_EXTENSIONS:
                continue

            key = str(
                path.resolve()
            )

            if key in processed:
                continue

            try:
                print(
                    f"New document detected: {path.name}"
                )

                result = process_new_file(
                    file_path=str(path),
                    existing_document_ids=(
                        existing_document_ids
                    ),
                    rules=rules or [],
                )

                processed.add(key)

                print(
                    "Incremental processing complete: "
                    f"run_id={result.get('run_id')} "
                    f"status={result.get('status')}"
                )

            except Exception as exc:
                print(
                    f"Failed to process "
                    f"{path.name}: {exc}"
                )

        time.sleep(poll_seconds)