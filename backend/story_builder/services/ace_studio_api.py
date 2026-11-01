"""HTTP seam for the standalone music workspace."""
import re
from . import ace_studio as studio


def handle(root, environ, start_response, read_json, respond):
    method, path = environ.get("REQUEST_METHOD", "GET"), environ.get("PATH_INFO", "")
    if path == "/api/ace/state" and method == "GET":
        result = studio.snapshot(root)
    elif path == "/api/ace/projects" and method == "POST":
        result = studio.add_project(root, read_json(environ))
    elif match := re.fullmatch(r"/api/ace/projects/([\w-]+)/(command|dataset|log)", path):
        project_id, operation = match.groups()
        if operation == "log" and method == "GET":
            with studio.state(root) as data:
                job_id = studio.project(data, project_id).get("job_id")
            result = {"text": "No runtime log yet."}
            if job_id:
                log = root / "ace_step/runs" / studio.ident(job_id) / "runtime.log"
                if log.is_file():
                    with log.open("rb") as stream:
                        stream.seek(max(0, log.stat().st_size - 12000))
                        result = {"text": stream.read().decode("utf-8", errors="replace")}
        elif method == "POST" and operation in {"command", "dataset"}:
            result = {"command": studio.command, "dataset": studio.dataset}[operation](root, project_id, read_json(environ))
        else:
            return respond(start_response, "405 Method Not Allowed", {"error": {"message": "Unsupported music operation."}})
    else:
        return respond(start_response, "404 Not Found", {"error": {"message": "Music endpoint not found."}})
    return respond(start_response, "200 OK", result)
