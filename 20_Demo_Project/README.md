Demo Project: TaskBoard – Homework
=================================

Name: Anshul Mohanty    Roll No: 24BCS10191    Section: A

See also: [LEARNING.md](LEARNING.md) - diagram and revision notes for this topic.

Session 21 is the capstone. The class repository has two parts: the **TaskBoard demo project** that was
built in class (the code in `session21-python/`), and a brief for a separate final project. This folder is
the **demo project**: I took TaskBoard, ran every stage of it on my machine and on GitHub, fixed what did
not work, and recorded the results below. It follows the 15-step "final demo" from the session README.

The folder was named `20_Capstone_TaskBoard` while the outputs below were captured, so the terminal window titles and a few command
lines still show that path; it was renamed to `20_Demo_Project` afterwards.

```mermaid
flowchart LR
    DEV["git push"] --> GA["GitHub Actions"]
    GA --> T["test<br/>pytest + npm build + helm lint"]
    T --> B["build 2 images<br/>tag = commit SHA"]
    B --> S["Trivy<br/>fail on fixable HIGH/CRITICAL"]
    S --> R["push to GHCR"]
    R --> D["deploy job<br/>helm upgrade on kind + smoke test"]
    R --> MK["minikube<br/>helm upgrade --set tag=SHA"]
    TF["Terraform<br/>VPC + EKS"] -.->|"cloud target"| MK
    MK --> ING["Ingress taskboard.local<br/>/ -> frontend, /api -> backend"]
    MK --> HPA["HPA 2..N backend pods"]
    MK --> MON["Prometheus + Grafana<br/>ServiceMonitor"]
```

| Folder | Contents |
|---|---|
| [backend/](backend/) | FastAPI + SQLAlchemy + Alembic, `/health`, `/ready`, `/metrics`, CRUD on `/api/tasks`, 12 pytest tests |
| [frontend/](frontend/) | React + Vite dashboard; multi-stage image (Node build → non-root nginx) |
| [docker-compose.yml](docker-compose.yml) | PostgreSQL + backend + frontend on one machine |
| [helm/taskboard/](helm/taskboard/) | Deployments, Services, PostgreSQL + PVC, Ingress, HPA, ServiceMonitor |
| [terraform/](terraform/) | AWS VPC (2 public + 2 private subnets, NAT) + EKS with a managed node group |
| [monitoring/](monitoring/) | kube-prometheus-stack values and the Grafana dashboard |
| [troubleshooting/](troubleshooting/) | The two deliberately broken manifests from class |
| [../.github/workflows/20-taskboard-cicd.yml](../.github/workflows/20-taskboard-cicd.yml) | The CI/CD pipeline |

### What I had to fix in the class code

Running every stage for real showed eight problems. Each is shown with output in the task it belongs to.

| # | Problem in the class code | Effect | Fix |
|---|---|---|---|
| 1 | Tests use `TestClient(app)` without `with` | Startup hook never runs → `no such table: tasks`, 1 of 3 tests fails, pipeline stops | `with TestClient(app)` fixture in `conftest.py`, 9 more tests (12 total) |
| 2 | Compose `depends_on` only waits for the Postgres *container* | Backend runs Alembic before Postgres accepts connections and exits | `pg_isready` healthcheck + `condition: service_healthy` |
| 3 | `e.currentTarget.reset()` after an `await` in the create-task form | Task is saved, but the modal never closes and the list never refreshes | Keep a reference to the form before the `await` |
| 4 | Three different names for the backend (`taskboard-taskboard-backend`, `taskboard-backend:8080`, `backend:8000`) | Ingress and the frontend's nginx proxy can never reach the API on Kubernetes | One naming helper; nginx gets the backend URL from an env var |
| 5 | Frontend runs nginx as root; old base images | Trivy: 44 fixable HIGH/CRITICAL in Alpine 3.21, 3 in Starlette 0.41 → pipeline fails | `nginx-unprivileged` (uid 101, port 8080), FastAPI 0.142, test tools out of the image |
| 6 | `ghcr.io/${{ github.repository_owner }}/...` | My owner name has capitals; Docker rejects upper-case image names | Lower-case `IMAGE_PREFIX` |
| 7 | Terraform blocks written on one line | `Invalid single-argument block definition` - `init` cannot even parse it | Proper HCL + a LocalStack switch |
| 8 | `package.json` pins everything to `latest`, no lock file | Every build can get different versions | Pinned versions + `package-lock.json`, `npm ci` |

---

Task 1: Application and API
---------------------------

### Tests first

![pytest](screenshots/01_pytest.png)

```
$ # pyt DIR REQS CMD = run CMD in python:3.12-slim (same Python as the backend image and the CI job)

$ # 1) the teacher's tests, unchanged
$ pyt 'D:/Devops_Nensi/devops-heros/session21-python/backend' requirements.txt 'pytest -q -p no:warnings 2>&1' | grep -E '^(E  +sqlalchemy.exc|FAILED|[0-9]+ (passed|failed))'
E       sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: tasks
FAILED tests/test_api.py::test_create_task_validation - sqlalchemy.exc.Operat...
1 failed, 2 passed in 1.60s

$ # 2) after the fix: TestClient used as a context manager, plus 9 more tests
$ grep -n -B1 -A3 'def client' backend/tests/conftest.py
15-@pytest.fixture(scope="session")
16:def client():
17-    # "with" runs the lifespan hook, which creates the tables.
18-    # A bare TestClient(app) never does, and every DB call fails with "no such table: tasks".
19-    with TestClient(app) as c:
$ pyt 'D:/DevOps Assignment/20_Capstone_TaskBoard/backend' requirements-dev.txt 'pytest -v 2>&1' | grep -E 'PASSED|FAILED| passed| failed'
tests/test_api.py::test_health PASSED                                    [  8%]
tests/test_api.py::test_ready_checks_the_database PASSED                 [ 16%]
tests/test_api.py::test_root PASSED                                      [ 25%]
tests/test_api.py::test_create_task PASSED                               [ 33%]
tests/test_api.py::test_create_task_rejects_bad_input PASSED             [ 41%]
tests/test_api.py::test_list_tasks_newest_first PASSED                   [ 50%]
tests/test_api.py::test_get_task PASSED                                  [ 58%]
tests/test_api.py::test_get_missing_task_returns_404 PASSED              [ 66%]
tests/test_api.py::test_update_task_status PASSED                        [ 75%]
tests/test_api.py::test_delete_task PASSED                               [ 83%]
tests/test_api.py::test_stats_count_by_status PASSED                     [ 91%]
tests/test_api.py::test_metrics_endpoint_is_prometheus_format PASSED     [100%]
============================== 12 passed in 0.21s ==============================
```

### Run it locally with Docker Compose

The class `docker-compose.yml` lost the race against PostgreSQL every time:

![compose race](screenshots/02_compose_race.png)

```
$ # the teacher's docker-compose.yml: depends_on only waits for the postgres CONTAINER to start
$ TEACHER=D:/Devops_Nensi/devops-heros/session21-python/docker-compose.yml
$ docker compose -p teacher -f $TEACHER up -d 2>&1 | grep -c Started
3
$ sleep 20; docker compose -p teacher -f $TEACHER ps -a --format "table {{.Service}}\t{{.Status}}"
SERVICE    STATUS
backend    Exited (1) 18 seconds ago
frontend   Up 20 seconds
postgres   Up 21 seconds
$ docker compose -p teacher -f $TEACHER logs backend --no-log-prefix 2>&1 | grep -E "^sqlalchemy.exc|Is the server"
	Is the server running on that host and accepting TCP/IP connections?
sqlalchemy.exc.OperationalError: (psycopg.OperationalError) connection failed: connection to server at "172.19.0.2", port 5432 failed: Connection refused
	Is the server running on that host and accepting TCP/IP connections?
$ docker compose -p teacher -f $TEACHER logs postgres --no-log-prefix 2>&1 | grep -E "ready to accept" | tail -1
2026-10-07 11:24:05.569 UTC [1] LOG:  database system is ready to accept connections
$ docker compose -p teacher -f $TEACHER down -v 2>&1 | tail -1
 Network teacher_default Removed

$ # fix: a pg_isready healthcheck, and the backend waits for service_healthy
$ grep -n -A4 -E 'healthcheck:|depends_on:' docker-compose.yml | grep -v -E 'retries|timeout|interval|^--$' | head -9
14:    healthcheck:
15-      test: ["CMD-SHELL", "pg_isready -U taskboard -d taskboard"]
24:    depends_on:
25-      postgres:
26-        condition: service_healthy
27-    ports:
28-      - "8000:8000"
34:    depends_on:
35-      - backend
```

With the healthcheck the backend starts only once the database is ready:

![compose up](screenshots/03_compose_up.png)

```
$ docker compose up -d --build 2>&1 | grep -E 'Built|Healthy|Started|Created' | sed 's/^ *//'
Image taskboard-backend Built
Image taskboard-frontend Built
Network taskboard_default Created
Volume taskboard_postgres-data Created
Container taskboard-postgres-1 Created
Container taskboard-backend-1 Created
Container taskboard-frontend-1 Created
Container taskboard-postgres-1 Started
Container taskboard-postgres-1 Healthy
Container taskboard-backend-1 Started
Container taskboard-frontend-1 Started
$ sleep 4; docker compose ps --format 'table {{.Service}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' | sed -E 's/0.0.0.0:([0-9]+)->([0-9]+)\/tcp, \[::\]:[0-9]+->[0-9]+\/tcp/:\1->\2/'
SERVICE    IMAGE                STATUS                   PORTS
backend    taskboard-backend    Up 4 seconds             :8000->8000
frontend   taskboard-frontend   Up 4 seconds             :3000->8080
postgres   postgres:16-alpine   Up 8 seconds (healthy)   :5432->5432
$ docker compose logs backend --no-log-prefix 2>&1 | grep -E 'alembic|Uvicorn running|Application startup'
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_create_tasks
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)

$ curl -s localhost:8000/health; echo
{"status":"UP"}
$ curl -s localhost:8000/ready; echo
{"status":"READY"}
$ curl -s localhost:8000/; echo
{"service":"TaskBoard API","version":"1.0.0","docs":"/docs"}
$ # the browser only talks to :3000 - nginx in the frontend container proxies /api to the backend
$ curl -s localhost:3000/api/tasks/stats; echo
{"total":0,"todo":0,"inProgress":0,"done":0}
$ curl -s localhost:3000/ | grep -o '<title>.*</title>'
<title>TaskBoard</title>
```

### The application

![TaskBoard dashboard](screenshots/25_ui_compose.png)

Creating a task through the modal (this is where bug 3 showed up - before the fix the browser console
showed `Cannot read properties of null (reading 'reset')` and the modal stayed open):

![create task](screenshots/26_ui_create_task.png)

### API - Swagger and CRUD

![Swagger](screenshots/27_swagger.png)

![CRUD](screenshots/04_crud_api.png)

```
$ # CREATE
$ curl -s -X POST localhost:8000/api/tasks -H 'Content-Type: application/json' -d '{"title":"Write Terraform for VPC + EKS","description":"Two public and two private subnets in ap-south-1","priority":"HIGH","assignee":"Anshul Mohanty"}'; echo
{"title":"Write Terraform for VPC + EKS","description":"Two public and two private subnets in ap-south-1","priority":"HIGH","status":"TODO","assignee":"Anshul Mohanty","id":1,"created_at":"2026-10-07T11:25:51.067956Z"}
$ # READ one
$ curl -s localhost:8000/api/tasks/1; echo
{"title":"Write Terraform for VPC + EKS","description":"Two public and two private subnets in ap-south-1","priority":"HIGH","status":"TODO","assignee":"Anshul Mohanty","id":1,"created_at":"2026-10-07T11:25:51.067956Z"}
$ # UPDATE - only the status, the other fields stay
$ curl -s -X PUT localhost:8000/api/tasks/1 -H 'Content-Type: application/json' -d '{"status":"IN_PROGRESS"}'; echo
{"title":"Write Terraform for VPC + EKS","description":"Two public and two private subnets in ap-south-1","priority":"HIGH","status":"IN_PROGRESS","assignee":"Anshul Mohanty","id":1,"created_at":"2026-10-07T11:25:51.067956Z"}
$ # DELETE, then READ again
$ curl -s -o /dev/null -w '%{http_code}\n' -X DELETE localhost:8000/api/tasks/1
204
$ curl -s localhost:8000/api/tasks/1; echo
{"detail":"Task not found"}
$ # validation comes from the Pydantic schema
$ curl -s -X POST localhost:8000/api/tasks -H 'Content-Type: application/json' -d '{"title":"x","priority":"URGENT"}' | head -c 150; echo
{"detail":[{"type":"literal_error","loc":["body","priority"],"msg":"Input should be 'LOW', 'MEDIUM' or 'HIGH'","input":"URGENT","ctx":{"expected":"'LO
```

### Database

![database](screenshots/05_database.png)

```
$ docker compose exec postgres psql -U taskboard -d taskboard -c '\dt'
              List of relations
 Schema |      Name       | Type  |   Owner
--------+-----------------+-------+-----------
 public | alembic_version | table | taskboard
 public | tasks           | table | taskboard
(2 rows)

$ docker compose exec postgres psql -U taskboard -d taskboard -c 'SELECT version_num FROM alembic_version'
    version_num
-------------------
 0001_create_tasks
(1 row)

$ docker compose exec postgres psql -U taskboard -d taskboard -c 'SELECT id, left(title, 34) AS title, priority, status, assignee FROM tasks ORDER BY id'
 id |               title                | priority |   status    |    assignee
----+------------------------------------+----------+-------------+----------------
  2 | Set up GitHub Actions pipeline     | HIGH     | DONE        | Anshul Mohanty
  3 | Containerise backend and frontend  | MEDIUM   | DONE        | Anshul Mohanty
  4 | Write Terraform for VPC + EKS      | HIGH     | DONE        | Anshul Mohanty
  5 | Package the app as a Helm chart    | HIGH     | IN_PROGRESS | Anshul Mohanty
  6 | Add ServiceMonitor for /metrics    | MEDIUM   | IN_PROGRESS | Riya Sharma
  7 | Load test the HPA                  | MEDIUM   | TODO        | Karan Mehta
  8 | Troubleshooting drill: broken imag | LOW      | TODO        | Riya Sharma
 12 | Present the capstone demo          | HIGH     | TODO        | Anshul Mohanty
(8 rows)

$ docker compose exec postgres psql -U taskboard -d taskboard -c 'SELECT status, count(*) FROM tasks GROUP BY status ORDER BY status'
   status    | count
-------------+-------
 DONE        |     3
 IN_PROGRESS |     2
 TODO        |     3
(3 rows)
```

---

Task 2: Docker and security scanning
------------------------------------

![images and non-root](screenshots/06_images_nonroot.png)

```
$ docker images --format 'table {{.Repository}}:{{.Tag}}\t{{.Size}}' | grep -E 'REPOSITORY|^taskboard-(backend|frontend)'
REPOSITORY:TAG                          SIZE
taskboard-frontend:latest               90.4MB
taskboard-backend:latest                306MB
taskboard-frontend:teacher              73.9MB
taskboard-backend:teacher               297MB
$ # both containers run as non-root users
$ docker compose exec backend id
uid=10001(appuser) gid=10001(appuser) groups=10001(appuser)
$ docker compose exec frontend id
uid=101(nginx) gid=101(nginx) groups=101(nginx)
$ docker compose exec frontend ps -o user,pid,args | head -3
USER     PID   COMMAND
nginx        1 nginx: master process nginx -g daemon off;
nginx       35 nginx: worker process
$ # frontend = multi-stage: node:22-alpine builds dist/, only dist/ is copied into nginx
$ grep -E '^(FROM|COPY --from|ENV|EXPOSE)' frontend/Dockerfile
FROM node:22-alpine AS build
FROM nginxinc/nginx-unprivileged:1.30-alpine
ENV BACKEND_URL=http://backend:8000
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
$ docker compose exec frontend sh -c 'ls /usr/share/nginx/html /usr/share/nginx/html/assets; which node npm || echo "no node/npm in the runtime image"'
/usr/share/nginx/html:
50x.html
assets
index.html

/usr/share/nginx/html/assets:
index-CNSSyWHq.js
index-DkMuKOF6.css
no node/npm in the runtime image
$ # the nginx config was rendered from the template at start-up with BACKEND_URL
$ docker compose exec frontend grep proxy_pass /etc/nginx/conf.d/default.conf
    proxy_pass http://backend:8000;
    proxy_pass http://backend:8000/health;
```

The backend image runs as `appuser` (uid 10001) and the frontend as `nginx` (uid 101). The runtime
frontend image contains only nginx and the built `dist/` - no Node, no `node_modules`.

### Trivy - the same gate the pipeline uses

![trivy](screenshots/07_trivy.png)

```
$ # the same check the pipeline runs: HIGH + CRITICAL, only vulnerabilities that already have a fix
$ trivy() { docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache/ aquasec/trivy:0.75.0 "$@"; }

$ # 1) the teacher's images as given
$ trivy image -q --severity HIGH,CRITICAL --ignore-unfixed --table-mode summary taskboard-backend:teacher | grep -E 'Target|debian|│ +[1-9]'
│                                      Target                                      │    Type    │ Vulnerabilities │ Secrets │
│ taskboard-backend:teacher (debian 13.7)                                          │   debian   │        0        │    -    │
│ usr/local/lib/python3.12/site-packages/starlette-0.41.3.dist-info/METADATA       │ python-pkg │        3        │    -    │
$ trivy image -q --severity HIGH,CRITICAL --ignore-unfixed --format json taskboard-backend:teacher | py -c "import json,sys; [print(v['Severity'], v['VulnerabilityID'], v['PkgName'], v['InstalledVersion'], '-> fixed in', v['FixedVersion']) for r in json.load(sys.stdin)['Results'] for v in r.get('Vulnerabilities') or []]"
HIGH CVE-2025-62727 starlette 0.41.3 -> fixed in 0.49.1
HIGH CVE-2026-48818 starlette 0.41.3 -> fixed in 1.1.0
HIGH CVE-2026-54283 starlette 0.41.3 -> fixed in 1.3.1
$ trivy image -q --severity HIGH,CRITICAL --ignore-unfixed --table-mode summary taskboard-frontend:teacher | grep -E 'Target|alpine'
│                   Target                   │  Type  │ Vulnerabilities │ Secrets │
│ taskboard-frontend:teacher (alpine 3.21.3) │ alpine │       44        │    -    │
$ trivy image -q --severity HIGH,CRITICAL --ignore-unfixed --format json taskboard-frontend:teacher | py -c "import json,sys,collections; c=collections.Counter(v['PkgName'] for r in json.load(sys.stdin)['Results'] for v in r.get('Vulnerabilities') or []); print(', '.join(f'{p} {n}' for p,n in c.most_common()))"
libcrypto3 10, libssl3 10, libexpat 7, libpng 6, libxml2 6, c-ares 1, musl 1, musl-utils 1, nghttp2-libs 1, zlib 1

$ # 2) after: FastAPI 0.142 (Starlette 1.7), nginx-unprivileged 1.30 on Alpine 3.24, test tools out of the image
$ trivy image -q --severity HIGH,CRITICAL --ignore-unfixed --table-mode summary taskboard-backend:latest | grep -E 'Target|debian|starlette|│ +[1-9]'
│                                      Target                                      │    Type    │ Vulnerabilities │ Secrets │
│ taskboard-backend:latest (debian 13.7)                                           │   debian   │        0        │    -    │
│ usr/local/lib/python3.12/site-packages/starlette-1.7.0.dist-info/METADATA        │ python-pkg │        0        │    -    │
$ trivy image -q --severity HIGH,CRITICAL --ignore-unfixed --table-mode summary taskboard-frontend:latest | grep -E 'Target|alpine|│ +[1-9]'
│                  Target                   │  Type  │ Vulnerabilities │ Secrets │
│ taskboard-frontend:latest (alpine 3.24.2) │ alpine │        0        │    -    │
$ trivy image -q --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 taskboard-backend:latest >/dev/null && trivy image -q --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 taskboard-frontend:latest >/dev/null; echo "exit code: $?"
exit code: 0
```

Trivy scanned the OS packages (Debian / Alpine) and every Python package inside the images. The class
images had 3 fixable HIGH CVEs in Starlette (e.g. CVE-2025-62727, a denial of service through the `Range`
header) and 44 fixable HIGH/CRITICAL in Alpine 3.21 (OpenSSL, libexpat, libxml2, ...). With `exit-code: 1`
the pipeline would have stopped there. Newer FastAPI/Starlette and nginx-unprivileged on Alpine 3.24 give
a clean scan, so the gate passes. A clean scan means "no *known, fixable* HIGH/CRITICAL today" - not "secure".

---

Task 3: Git and the CI/CD pipeline
----------------------------------

[.github/workflows/20-taskboard-cicd.yml](../.github/workflows/20-taskboard-cicd.yml) - path-filtered to
this folder, like topics 15 and 16:

| Job | Steps |
|---|---|
| Test backend + build frontend | Python 3.12 → `pip install -r requirements-dev.txt` → `pytest -v`; Node 22 → `npm ci` → `npm run build`; `helm lint` |
| Build, scan and push images | build both images tagged with `github.sha` (+ OCI source label) → Trivy backend → Trivy frontend → login → push to GHCR (main only) |
| Deploy with Helm | kind cluster on the runner → GHCR pull secret → `helm upgrade --install --set *.tag=$GITHUB_SHA --wait` → smoke test through the frontend Service (page, `/health`, POST a task, stats) |

The class pipeline deploys with a `KUBE_CONFIG_DATA` secret pointing at a real cluster. I have no cloud
cluster, so - as in topic 16 - the deploy job creates a throw-away kind cluster on the runner and deploys
the exact images it just pushed.

### Run #1 - the first commit

![pipeline run 1](screenshots/29_pipeline_run1.png)

| Test | Build, scan, push | Deploy |
|---|---|---|
| ![test](screenshots/30_job_test.png) | ![build](screenshots/31_job_build_scan_push.png) | ![deploy](screenshots/32_job_deploy.png) |

### A small application change → run #2

![git change](screenshots/19_git_change.png)

```
$ # a small application change: the API reports version 1.1.0 (and a test that checks it)
$ git diff --stat
 20_Capstone_TaskBoard/backend/app/main.py       | 4 ++--
 20_Capstone_TaskBoard/backend/tests/test_api.py | 1 +
 20_Capstone_TaskBoard/helm/taskboard/Chart.yaml | 4 ++--
 3 files changed, 5 insertions(+), 4 deletions(-)
$ git diff -U0 -- backend/app/main.py backend/tests/test_api.py | grep -E '^[-+][^-+]'
-app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
+app = FastAPI(title=settings.app_name, version="1.1.0", lifespan=lifespan)
-    return {"service": settings.app_name, "version": "1.0.0", "docs": "/docs"}
+    return {"service": settings.app_name, "version": "1.1.0", "docs": "/docs"}
+    assert response.json()["version"] == "1.1.0"
$ git add backend/app/main.py backend/tests/test_api.py helm/taskboard/Chart.yaml
$ git -c core.safecrlf=false commit -q -m 'TaskBoard API 1.1.0: report the new version from /' && git log --oneline -3
f771edc TaskBoard API 1.1.0: report the new version from /
4c4169d Add the TaskBoard Grafana dashboard and minikube monitoring settings
2d48b0c Add topic 20: TaskBoard capstone app, Helm chart, Terraform and CI/CD pipeline
$ git push origin main 2>&1 | tail -1
   2d48b0c..f771edc  main -> main
```

![pipeline run 2](screenshots/33_pipeline_run2.png)

### Container registry

![GHCR](screenshots/34_ghcr_packages.png)

`taskboard-backend` and `taskboard-frontend` are public (they inherit the repository's visibility through
the `org.opencontainers.image.source` label), tagged with the full commit SHA - so every running pod can be
traced back to the commit that built it.

---

Task 4: Terraform - AWS VPC + EKS
---------------------------------

No AWS account, so - as in topics 17 and 18 - the AWS APIs come from **LocalStack 4.14** in Docker.
The code is ordinary AWS Terraform using the `terraform-aws-modules/vpc` and `eks` modules;
`use_localstack = false` (the default) targets real AWS.

The class code could not even be parsed:

![teacher terraform](screenshots/09_tf_teacher.png)

```
$ # the teacher's terraform/ as given - every block written on one line
$ cut -c1-118 D:/Devops_Nensi/devops-heros/session21-python/terraform/main.tf
module "vpc" { source = "terraform-aws-modules/vpc/aws" version = "5.8.1" name = "taskboard-vpc" cidr = "10.20.0.0/16"
module "eks" { source = "terraform-aws-modules/eks/aws" version = "20.37.1" cluster_name = var.cluster_name cluster_ve
$ terraform -chdir=D:/Devops_Nensi/devops-heros/session21-python/terraform validate -no-color 2>&1 | grep -E '^(Error|  on )|single-line' | sort | uniq -c
      1   on main.tf line 1, in module "vpc":
      1   on versions.tf line 1, in terraform:
      2 A single-line block definition must end with a closing brace immediately
      2 Error: Invalid single-argument block definition
```

### init, validate, plan

![plan](screenshots/10_tf_plan.png)

```
$ # AWS APIs come from LocalStack 4.14 in Docker (no AWS account) - same code, use_localstack = true
$ docker ps --filter name=localstack --format '{{.Names}}  {{.Image}}  {{.Status}}'
localstack  localstack/localstack:4.14  Up 3 minutes (healthy)
$ grep -v '^#' localstack.tfvars
use_localstack = true
$ terraform fmt -recursive -check && echo 'fmt: OK'
fmt: OK
$ terraform init -no-color | grep -E 'Initializing|Installed|Reusing|successfully'
Initializing the backend...
Initializing modules...
Initializing provider plugins...
- Reusing previous version of hashicorp/time from the dependency lock file
- Reusing previous version of hashicorp/tls from the dependency lock file
- Reusing previous version of hashicorp/cloudinit from the dependency lock file
- Reusing previous version of hashicorp/null from the dependency lock file
- Reusing previous version of hashicorp/aws from the dependency lock file
Terraform has been successfully initialized!
$ terraform validate -no-color
Success! The configuration is valid.

$ terraform plan -no-color -var-file=localstack.tfvars -out=tfplan > plan.txt; grep -E '^Plan:' plan.txt
Plan: 54 to add, 0 to change, 0 to destroy.
$ # the 54 resources: by module, then by type
$ grep -E '^  # .* will be created' plan.txt | grep -oE '^  # module\.[a-z]+' | sort | uniq -c
     35   # module.eks
     19   # module.vpc
$ grep -E '^  # .* will be created' plan.txt | grep -oE '(aws|null|time)_[a-z_]+\.' | tr -d . | sort | uniq -c | sort -rn | paste - - | column -t
11  aws_security_group_rule            7  aws_iam_role_policy_attachment
4   aws_subnet                         4  aws_route_table_association
2   aws_security_group                 2  aws_route_table
2   aws_route                          2  aws_iam_role
2   aws_iam_policy                     1  time_sleep
1   null_resource                      1  aws_vpc
1   aws_nat_gateway                    1  aws_launch_template
1   aws_kms_key                        1  aws_kms_alias
1   aws_internet_gateway               1  aws_iam_openid_connect_provider
1   aws_eks_node_group                 1  aws_eks_cluster
1   aws_eks_access_policy_association  1  aws_eks_access_entry
1   aws_eip                            1  aws_default_security_group
1   aws_default_route_table            1  aws_default_network_acl
1   aws_cloudwatch_log_group
$ # a few of the planned values
$ awk '/resource "aws_subnet" "public"/,/^    }/' plan.txt | grep -E '  \+ (availability_zone|cidr_block) '
      + availability_zone                              = "ap-south-1a"
      + cidr_block                                     = "10.20.101.0/24"
      + availability_zone                              = "ap-south-1b"
      + cidr_block                                     = "10.20.102.0/24"
$ awk '/resource "aws_eks_cluster" "this"/,/^    }/' plan.txt | grep -E '^      \+ (name|version) '
      + name                          = "taskboard-eks"
      + version                       = "1.34"
$ awk '/resource "aws_eks_node_group" "this"/,/^    }/' plan.txt | grep -E '"t3|_size'
      + disk_size              = (known after apply)
          + "t3.medium",
          + desired_size = 2
          + max_size     = 4
          + min_size     = 2
```

### apply - the network

![apply vpc](screenshots/11_tf_apply_vpc.png)

```
$ # 1) the network first: -target applies only module.vpc and what it depends on
$ terraform apply -no-color -auto-approve -var-file=localstack.tfvars -target=module.vpc 2>&1 | grep -E 'Creation complete|Apply complete' | sed -E 's/: Creation complete after [0-9]+s//' | sed -E 's/ \[id=.*\]//'
module.vpc.aws_vpc.this[0]
module.vpc.aws_subnet.private[0]
module.vpc.aws_subnet.public[0]
module.vpc.aws_subnet.public[1]
module.vpc.aws_subnet.private[1]
module.vpc.aws_default_route_table.default[0]
module.vpc.aws_route_table.private[0]
module.vpc.aws_internet_gateway.this[0]
module.vpc.aws_route_table.public[0]
module.vpc.aws_default_security_group.this[0]
module.vpc.aws_route_table_association.private[0]
module.vpc.aws_route_table_association.private[1]
module.vpc.aws_route_table_association.public[0]
module.vpc.aws_route_table_association.public[1]
module.vpc.aws_eip.nat[0]
module.vpc.aws_default_network_acl.this[0]
module.vpc.aws_nat_gateway.this[0]
module.vpc.aws_route.public_internet_gateway[0]
module.vpc.aws_route.private_nat_gateway[0]
Apply complete! Resources: 19 added, 0 changed, 0 destroyed.

$ # verify with the AWS CLI (awslocal = the AWS CLI inside the LocalStack container)
$ awslocal() { docker exec -e AWS_DEFAULT_REGION=ap-south-1 localstack awslocal "$@"; }
$ awslocal ec2 describe-vpcs --filters Name=tag:Name,Values=taskboard-vpc --query 'Vpcs[].[VpcId,CidrBlock,Tags[?Key==`ManagedBy`]|[0].Value]' --output text
vpc-1850624fdd06293ff	10.20.0.0/16	terraform
$ awslocal ec2 describe-subnets --filters Name=vpc-id,Values=$(terraform output -raw vpc_id) --query 'sort_by(Subnets,&CidrBlock)[].[CidrBlock,AvailabilityZone,Tags[?Key==`Name`]|[0].Value]' --output table
------------------------------------------------------------------------
|                            DescribeSubnets                           |
+-----------------+--------------+-------------------------------------+
|  10.20.1.0/24   |  ap-south-1a |  taskboard-vpc-private-ap-south-1a  |
|  10.20.101.0/24 |  ap-south-1a |  taskboard-vpc-public-ap-south-1a   |
|  10.20.102.0/24 |  ap-south-1b |  taskboard-vpc-public-ap-south-1b   |
|  10.20.2.0/24   |  ap-south-1b |  taskboard-vpc-private-ap-south-1b  |
+-----------------+--------------+-------------------------------------+
$ awslocal ec2 describe-nat-gateways --query 'NatGateways[].[NatGatewayId,State,SubnetId]' --output text
nat-da97066fa4ec259d6	available	subnet-0e173865db999189f
$ awslocal ec2 describe-internet-gateways --filters Name=attachment.vpc-id,Values=$(terraform output -raw vpc_id) --query 'InternetGateways[].InternetGatewayId' --output text
igw-f521f304db0b5589c
```

### apply - EKS

![apply eks](screenshots/12_tf_eks.png)

```
$ # 2) everything else - the EKS module
$ terraform apply -no-color -auto-approve -var-file=localstack.tfvars > apply-full.log 2>&1; echo "exit code: $?"
exit code: 1
$ grep 'Creation complete' apply-full.log | grep -oE 'aws_[a-z_]+\.' | tr -d . | sort | uniq -c | sort -rn | paste - - | column -t
11  aws_security_group_rule  7  aws_iam_role_policy_attachment
2   aws_security_group       2  aws_iam_role
2   aws_iam_policy           1  aws_kms_key
1   aws_kms_alias            1  aws_cloudwatch_log_group
$ grep -A4 '^Error' apply-full.log | sed -E 's/, RequestID: [a-f0-9-]+//' | fold -w 140
Error: creating EKS Cluster (taskboard-eks): operation error EKS: CreateCluster, https response error StatusCode: 501, api error InternalFai
lure: The API for service eks is either not included in your current license plan or has not yet been emulated by LocalStack.

  with module.eks.aws_eks_cluster.this[0],
  on .terraform\modules\eks\main.tf line 35, in resource "aws_eks_cluster" "this":
  35: resource "aws_eks_cluster" "this" {
$ # IAM roles, KMS key, log group and security groups were created; the cluster itself needs the EKS API,
$ # which LocalStack only emulates in its paid edition - on a real AWS account this step creates the cluster
$ terraform state list | grep -vE '(^|\.)data\.' | grep -c ''
46
$ terraform state list | grep -E 'eks_cluster|eks_node_group|kms_key|iam_role\.this'
module.eks.aws_iam_role.this[0]
module.eks.module.eks_managed_node_group["main"].aws_iam_role.this[0]
module.eks.module.kms.aws_kms_key.this[0]
```

27 of the EKS module's resources (IAM roles and policies, KMS key, log group, security groups) were
created; the cluster itself stops at `CreateCluster` because LocalStack's free edition does not include
the EKS API. On a real account the same `terraform apply` continues with the cluster and the node group
(~10-15 minutes), and `terraform output configure_kubectl` prints the `aws eks update-kubeconfig` command.

### destroy

![destroy](screenshots/13_tf_destroy.png)

```
$ terraform destroy -no-color -auto-approve -var-file=localstack.tfvars 2>&1 | grep -E 'Destruction complete|Destroy complete' | grep -oE '(aws|null|time)_[a-z_]+\.|Destroy complete.*' | tr -d . | sort | uniq -c | sort -rn
     11 aws_security_group_rule
      7 aws_iam_role_policy_attachment
      4 aws_subnet
      4 aws_route_table_association
      2 aws_security_group
      2 aws_route_table
      2 aws_route
      2 aws_iam_role
      2 aws_iam_policy
      1 aws_vpc
      1 aws_nat_gateway
      1 aws_kms_key
      1 aws_kms_alias
      1 aws_internet_gateway
      1 aws_eip
      1 aws_default_security_group
      1 aws_default_route_table
      1 aws_default_network_acl
      1 aws_cloudwatch_log_group
      1 Destroy complete! Resources: 46 destroyed
$ terraform state list | grep -c ''
0
$ docker exec -e AWS_DEFAULT_REGION=ap-south-1 localstack awslocal ec2 describe-vpcs --filters Name=tag:Name,Values=taskboard-vpc --query 'length(Vpcs)'
0
$ docker exec -e AWS_DEFAULT_REGION=ap-south-1 localstack awslocal ec2 describe-nat-gateways --query 'NatGateways[].State' --output text
deleted
```

---

Task 5: Kubernetes and Helm
---------------------------

Cluster: minikube profile `devops` (Kubernetes 1.37), with the ingress and metrics-server addons and
kube-prometheus-stack already installed (Task 7).

### The chart, before and after

![helm names](screenshots/08_helm_names.png)

```
$ # 1) the teacher's chart, rendered: which name does each piece use for the backend?
$ TCHART=D:/Devops_Nensi/devops-heros/session21-python
$ helm template taskboard $TCHART/helm/taskboard --set ingress.enabled=true | grep -A3 -E '^kind: Service$' | grep -oE 'name: [a-z-]+'
name: taskboard-taskboard-backend
name: taskboard-frontend
name: taskboard-postgres
$ helm template taskboard $TCHART/helm/taskboard --set ingress.enabled=true | grep -E 'path: /api'
      - {path: /api, pathType: Prefix, backend: {service: {name: taskboard-backend, port: {number: 8080}}}}
$ grep proxy_pass $TCHART/frontend/nginx.conf
    proxy_pass http://backend:8000;
    proxy_pass http://backend:8000/health;
$ grep -E '^FROM|USER|EXPOSE' $TCHART/frontend/Dockerfile
FROM node:22-alpine AS build
FROM nginx:1.27-alpine
EXPOSE 80
$ # -> Service is taskboard-taskboard-backend:8000, the Ingress wants taskboard-backend:8080, nginx wants backend:8000
$ # -> and the frontend runs nginx as root on port 80

$ # 2) mine: every name comes from one helper, the frontend gets the backend URL from the chart
$ helm lint helm/taskboard -f helm/taskboard/values-minikube.yaml | tail -1
1 chart(s) linted, 0 chart(s) failed
$ helm template taskboard helm/taskboard -f helm/taskboard/values-minikube.yaml | grep -A3 -E '^kind: Service$' | grep -oE 'name: [a-z-]+'
name: taskboard-backend
name: taskboard-frontend
name: taskboard-postgres
$ helm template taskboard helm/taskboard -f helm/taskboard/values-minikube.yaml | grep -E 'path: /api|BACKEND_URL|scaleTargetRef'
        - {name: BACKEND_URL, value: "http://taskboard-backend:8000"}
  scaleTargetRef: {apiVersion: apps/v1, kind: Deployment, name: taskboard-backend}
      - {path: /api, pathType: Prefix, backend: {service: {name: taskboard-backend, port: {number: 8000}}}}
```

Other chart changes: an init container that waits for PostgreSQL (the backend runs Alembic on start),
`replicas` left out of the backend Deployment when the HPA owns it, `Recreate` strategy for PostgreSQL's
ReadWriteOnce volume, `PGDATA` in a sub-directory (a fresh EBS volume has `lost+found`), the database
password read from the Secret, and the ServiceMonitor rendered only when its CRD exists.

### Deploying the images CI built

![deploy](screenshots/14_k8s_deploy.png)

```
$ # deploy the exact images CI built and pushed for commit 2d48b0c (pulled from GHCR, not built locally)
$ SHA=$(git rev-parse HEAD); echo $SHA
2d48b0c3e6ccec8114136e1d84121225cbebb9e2
$ kubectl apply -f k8s/namespace.yaml
namespace/taskboard created
$ helm upgrade --install taskboard ./helm/taskboard -n taskboard -f helm/taskboard/values-minikube.yaml --set backend.tag=$SHA --set frontend.tag=$SHA --wait --timeout 10m 2>&1 | grep -E 'NAME|STATUS|REVISION|NAMESPACE'
NAME: taskboard
NAMESPACE: taskboard
STATUS: deployed
REVISION: 1

$ helm list -n taskboard
NAME     	NAMESPACE	REVISION	UPDATED                              	STATUS  	CHART          	APP VERSION
taskboard	taskboard	1       	2026-10-07 17:20:54.5777427 +0530 IST	deployed	taskboard-1.0.0	1.0.0
$ kubectl get pods -n taskboard -o wide | awk '{print $1, $2, $3, $4, $5, $6}' | column -t
NAME                                 READY  STATUS   RESTARTS  AGE    IP
taskboard-backend-fd9cf8b97-72vf9    1/1    Running  0         3m21s  10.244.0.14
taskboard-backend-fd9cf8b97-bmqlx    1/1    Running  0         3m23s  10.244.0.17
taskboard-frontend-8d88fd487-9gbgv   1/1    Running  0         3m23s  10.244.0.18
taskboard-frontend-8d88fd487-nhnmv   1/1    Running  0         3m23s  10.244.0.16
taskboard-postgres-5854dd74cd-khdkq  1/1    Running  0         3m23s  10.244.0.15
$ kubectl get svc,ingress,hpa,pvc -n taskboard
NAME                         TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
service/taskboard-backend    ClusterIP   10.110.32.244   <none>        8000/TCP   3m24s
service/taskboard-frontend   ClusterIP   10.106.67.20    <none>        80/TCP     3m24s
service/taskboard-postgres   ClusterIP   10.102.56.0     <none>        5432/TCP   3m24s

NAME                                  CLASS   HOSTS             ADDRESS        PORTS   AGE
ingress.networking.k8s.io/taskboard   nginx   taskboard.local   192.168.58.2   80      3m23s

NAME                                                    REFERENCE                      TARGETS              MINPODS   MAXPODS   REPLICAS   AGE
horizontalpodautoscaler.autoscaling/taskboard-backend   Deployment/taskboard-backend   cpu: <unknown>/60%   2         6         2          3m24s

NAME                                            STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
persistentvolumeclaim/taskboard-postgres-data   Bound    pvc-0999fc81-fb5b-4ece-973b-eed91d100bfe   1Gi        RWO            standard       <unset>                 3m24s
$ kubectl get deploy -n taskboard -o custom-columns='DEPLOYMENT:.metadata.name,READY:.status.readyReplicas,IMAGE:.spec.template.spec.containers[0].image' | sed -E 's/:([0-9a-f]{7})[0-9a-f]{33}/:\1.../'
DEPLOYMENT           READY   IMAGE
taskboard-backend    2       ghcr.io/anshulmohanty/taskboard-backend:2d48b0c...
taskboard-frontend   2       ghcr.io/anshulmohanty/taskboard-frontend:2d48b0c...
taskboard-postgres   1       postgres:16-alpine
$ # the ServiceMonitor was rendered because the Prometheus Operator CRD exists in this cluster
$ kubectl get servicemonitor -n taskboard
NAME                AGE
taskboard-backend   3m34s
$ # the init container held the backend until PostgreSQL answered - hence 0 restarts
$ kubectl logs -n taskboard deploy/taskboard-backend -c wait-for-postgres | sort | uniq -c
Found 2 pods, using pod/taskboard-backend-fd9cf8b97-72vf9
      1 taskboard-postgres:5432 - accepting connections
     14 taskboard-postgres:5432 - no response
     14 waiting for postgres
$ kubectl logs -n taskboard deploy/taskboard-backend -c backend | grep -E 'alembic.runtime.migration\] Running|Uvicorn running'
Found 2 pods, using pod/taskboard-backend-fd9cf8b97-72vf9
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_create_tasks
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Upgrade to the next commit, rollback, roll forward

![upgrade](screenshots/22_helm_upgrade.png)

```
$ # CI run #2 published images for f771edc - roll the cluster forward to them
$ kubectl exec -n taskboard toolbox -- curl -s taskboard-backend:8000/; echo
{"service":"TaskBoard API","version":"1.0.0","docs":"/docs"}
$ SHA=$(git rev-parse HEAD); git log --oneline -1
f771edc TaskBoard API 1.1.0: report the new version from /
$ helm upgrade taskboard ./helm/taskboard -n taskboard -f helm/taskboard/values-minikube.yaml --set backend.tag=$SHA --set frontend.tag=$SHA --wait --timeout 10m 2>&1 | grep -E 'STATUS|REVISION'
STATUS: deployed
REVISION: 2
$ kubectl get deploy -n taskboard -o custom-columns='DEPLOYMENT:.metadata.name,READY:.status.readyReplicas,IMAGE:.spec.template.spec.containers[0].image' | sed -E 's/:([0-9a-f]{7})[0-9a-f]{33}/:\1.../'
DEPLOYMENT           READY   IMAGE
taskboard-backend    2       ghcr.io/anshulmohanty/taskboard-backend:f771edc...
taskboard-frontend   2       ghcr.io/anshulmohanty/taskboard-frontend:f771edc...
taskboard-postgres   1       postgres:16-alpine
$ kubectl exec -n taskboard toolbox -- curl -s taskboard-backend:8000/; echo
{"service":"TaskBoard API","version":"1.1.0","docs":"/docs"}
$ # the data survived the rollout - it lives on the PVC, not in the pods
$ kubectl exec -n taskboard toolbox -- curl -s taskboard-backend:8000/api/tasks/stats; echo
{"total":8,"todo":3,"inProgress":2,"done":3}
$ kubectl get hpa -n taskboard --no-headers | awk '{print $1, "min="$5, "max="$6, "replicas="$7}'
taskboard-backend min=2 max=4 replicas=2

$ helm history taskboard -n taskboard
REVISION	UPDATED                 	STATUS    	CHART          	APP VERSION	DESCRIPTION
1       	Wed Oct  7 17:20:54 2026	superseded	taskboard-1.0.0	1.0.0      	Install complete
2       	Wed Oct  7 18:51:56 2026	deployed  	taskboard-1.1.0	1.1.0      	Upgrade complete
```

![rollback](screenshots/23_helm_rollback.png)

```
$ # a bad release? roll back to revision 1 - Helm re-applies that revision's manifests (old image tags included)
$ helm rollback taskboard 1 -n taskboard --wait --timeout 10m
Rollback was a success! Happy Helming!
$ kubectl exec -n taskboard toolbox -- curl -s taskboard-backend:8000/; echo
{"service":"TaskBoard API","version":"1.0.0","docs":"/docs"}
$ kubectl get deploy taskboard-backend -n taskboard -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}' | sed -E 's/:([0-9a-f]{7})[0-9a-f]{33}/:\1.../'
ghcr.io/anshulmohanty/taskboard-backend:2d48b0c...
$ # and forward again to the release from CI run #2
$ helm rollback taskboard 2 -n taskboard --wait --timeout 10m
Rollback was a success! Happy Helming!
$ kubectl exec -n taskboard toolbox -- curl -s taskboard-backend:8000/; echo
{"service":"TaskBoard API","version":"1.1.0","docs":"/docs"}
$ helm history taskboard -n taskboard
REVISION	UPDATED                 	STATUS    	CHART          	APP VERSION	DESCRIPTION
1       	Wed Oct  7 17:20:54 2026	superseded	taskboard-1.0.0	1.0.0      	Install complete
2       	Wed Oct  7 18:51:56 2026	superseded	taskboard-1.1.0	1.1.0      	Upgrade complete
3       	Wed Oct  7 18:53:12 2026	superseded	taskboard-1.0.0	1.0.0      	Rollback to 1
4       	Wed Oct  7 18:55:51 2026	deployed  	taskboard-1.1.0	1.1.0      	Rollback to 2
$ kubectl rollout history deploy/taskboard-backend -n taskboard | tail -n +2 | head -6
REVISION  CHANGE-CAUSE
3         <none>
4         <none>
```

---

Task 6: Ingress and HPA
-----------------------

### Ingress

![ingress](screenshots/15_ingress.png)

```
$ # one Ingress, two routes: /api -> taskboard-backend:8000, / -> taskboard-frontend:80
$ kubectl describe ingress taskboard -n taskboard | sed -n '/Rules:/,/Annotations/p' | grep -v Annotations
Rules:
  Host             Path  Backends
  ----             ----  --------
  taskboard.local
                   /api   taskboard-backend:8000 (10.244.0.14:8000,10.244.0.17:8000)
                   /      taskboard-frontend:80 (10.244.0.16:8080,10.244.0.18:8080)
$ # minikube (docker driver) on Windows: the node IP is not routable, so reach the ingress controller via port-forward
$ kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 8080:80 &

$ curl -s -H 'Host: taskboard.local' localhost:8080/ | grep -o '<title>.*</title>'
<title>TaskBoard</title>
$ curl -s -H 'Host: taskboard.local' localhost:8080/api/tasks/stats; echo
{"total":0,"todo":0,"inProgress":0,"done":0}
$ curl -s -X POST -H 'Host: taskboard.local' -H 'Content-Type: application/json' localhost:8080/api/tasks -d '{"title":"Created through the Ingress","priority":"MEDIUM","assignee":"Anshul Mohanty"}'; echo
{"title":"Created through the Ingress","description":"","priority":"MEDIUM","status":"TODO","assignee":"Anshul Mohanty","id":2,"created_at":"2026-10-07T11:55:07.225583Z"}
$ # a host the Ingress does not know gets the controller's default 404
$ curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: other.local' localhost:8080/
404
$ # the controller's access log: which upstream served each request
$ kubectl logs -n ingress-nginx deploy/ingress-nginx-controller --tail 20 | grep -E 'taskboard-(backend|frontend)' | tail -3 | awk '{print $6, $7, $9, "->", $(NF-6)}'
"GET / 200 -> [taskboard-taskboard-frontend-80]
"GET /api/tasks/stats 200 -> [taskboard-taskboard-backend-8000]
"POST /api/tasks 201 -> [taskboard-taskboard-backend-8000]
```

The upstream names in the controller's log are `<namespace>-<service>-<port>`. The application through the
Ingress hostname (`taskboard.local` mapped to the port-forward in the browser):

![ingress UI](screenshots/28_ui_ingress.png)

### HPA - first attempt overloaded the node

![hpa overload](screenshots/17_hpa_overload.png)

```
$ # HPA: 2-6 backend pods, target 60% of the 100m CPU request (metrics from metrics-server)
$ kubectl get hpa -n taskboard
NAME                REFERENCE                      TARGETS       MINPODS   MAXPODS   REPLICAS   AGE
taskboard-backend   Deployment/taskboard-backend   cpu: 8%/60%   2         6         2          52m
$ kubectl top pods -n taskboard -l app=taskboard-backend
NAME                                CPU(cores)   MEMORY(bytes)
taskboard-backend-fd9cf8b97-72vf9   7m           45Mi
taskboard-backend-fd9cf8b97-bmqlx   9m           44Mi

$ # load from inside the cluster: scripts/load-test.sh in a curl pod, 30 requests in parallel against /api/tasks
$ kubectl run load -n taskboard --restart=Never --image=curlimages/curl --env REQUESTS=150000 --env CONCURRENCY=30 --command -- sh -c "$(cat scripts/load-test.sh)"
pod/load created
$ for i in $(seq 1 11); do sleep 20; printf '%s  ' "$(date +%T)"; kubectl get hpa taskboard-backend -n taskboard --no-headers | awk '{print $3, $4, "replicas="$7}'; done
18:13:46  cpu: 8%/60% replicas=2
18:14:06  cpu: 31%/60% replicas=2
18:14:27  cpu: 31%/60% replicas=2
18:14:47  cpu: 31%/60% replicas=2
18:15:08  cpu: 414%/60% replicas=2
18:15:29  cpu: 414%/60% replicas=4
18:16:03  Unable to connect to the server: net/http: TLS handshake timeout
18:16:34  Unable to connect to the server: net/http: TLS handshake timeout
18:17:04  Unable to connect to the server: net/http: TLS handshake timeout
18:17:34  Unable to connect to the server: net/http: TLS handshake timeout
18:18:05  Unable to connect to the server: net/http: TLS handshake timeout

$ # the API server stopped answering: the whole minikube node is one Docker container capped at 2.7 GiB
$ docker stats --no-stream --format '{{.Name}}  CPU={{.CPUPerc}}  MEM={{.MemUsage}}' devops
devops  CPU=75.92%  MEM=2.41GiB / 2.734GiB
$ # once the API answered again the load pod was force-deleted (kubectl delete pod load --grace-period=0 --force)

$ # after the load stopped
$ kubectl describe hpa taskboard-backend -n taskboard | grep SuccessfulRescale | sed -E 's/ +/ /g'
 Normal SuccessfulRescale 7m56s horizontal-pod-autoscaler New size: 4; reason: cpu resource utilization (percentage of request) above target
 Normal SuccessfulRescale 7m38s horizontal-pod-autoscaler New size: 6; reason: cpu resource utilization (percentage of request) above target
$ kubectl get pods -n taskboard -l app=taskboard-backend
NAME                                READY   STATUS    RESTARTS        AGE
taskboard-backend-fd9cf8b97-72vf9   1/1     Running   1 (2m19s ago)   61m
taskboard-backend-fd9cf8b97-bmqlx   1/1     Running   1 (2m17s ago)   62m
taskboard-backend-fd9cf8b97-ncvhb   1/1     Running   1 (2m18s ago)   7m55s
taskboard-backend-fd9cf8b97-w7tkm   1/1     Running   0               7m37s
taskboard-backend-fd9cf8b97-ww2g2   1/1     Running   0               7m37s
taskboard-backend-fd9cf8b97-zcl7t   1/1     Running   1 (2m19s ago)   7m55s
$ kubectl get events -n taskboard --field-selector reason=Unhealthy -o custom-columns='POD:.involvedObject.name,COUNT:.count,MESSAGE:.message' | grep -E 'POD|Liveness' | cut -c1-150 | head -5
POD                                   COUNT   MESSAGE
taskboard-backend-fd9cf8b97-72vf9     6       Liveness probe failed: Get "http://10.244.0.14:8000/health": context deadline exceeded (Client.Timeout e
taskboard-backend-fd9cf8b97-72vf9     1       Liveness probe failed: Get "http://10.244.0.14:8000/health": dial tcp 10.244.0.14:8000: connect: connect
taskboard-backend-fd9cf8b97-bmqlx     3       Liveness probe failed: Get "http://10.244.0.17:8000/health": context deadline exceeded (Client.Timeout e
taskboard-backend-fd9cf8b97-ncvhb     3       Liveness probe failed: Get "http://10.244.0.22:8000/health": dial tcp 10.244.0.22:8000: connect: connect
```

The HPA did its job (2 → 4 → 6 within 20 seconds of the CPU jump to 414%), but 30 parallel clients plus
6 backend pods plus the monitoring stack were more than the minikube node could give: it is a single Docker
container capped at ~2.7 GiB and 4 CPUs. The API server stopped answering, liveness probes timed out and
four pods were restarted. The HPA adds *pods*; it cannot add *capacity* - on EKS that is the node group's
job (`min_size 2, max_size 4` in Terraform) together with a cluster autoscaler.

Scale-down is slow on purpose - the HPA keeps the highest recommendation of the last 5 minutes:

![hpa down](screenshots/18_hpa_scale_down.png)

```
$ # scale-down is deliberately slow: the HPA keeps the highest recommendation of the last 5 minutes
$ kubectl describe hpa taskboard-backend -n taskboard | grep -E 'AbleToScale' | sed -E 's/ +/ /g'
 AbleToScale True ScaleDownStabilized recent recommendations were higher than current one, applying the highest recent recommendation
$ until [ "$(kubectl get hpa taskboard-backend -n taskboard -o jsonpath='{.status.currentReplicas}')" = 2 ]; do printf '%s  ' "$(date +%T)"; kubectl get hpa taskboard-backend -n taskboard --no-headers | awk '{print $3, $4, "replicas="$7}'; sleep 30; done; printf '%s  ' "$(date +%T)"; kubectl get hpa taskboard-backend -n taskboard --no-headers | awk '{print $3, $4, "replicas="$7}'
18:33:47  cpu: 2%/60% replicas=6
18:34:17  cpu: 16%/60% replicas=6
18:34:47  cpu: 16%/60% replicas=6
18:35:18  cpu: 16%/60% replicas=6
18:35:48  cpu: 2%/60% replicas=6
18:36:21  cpu: 2%/60% replicas=6
18:37:02  cpu: 2%/60% replicas=6
18:37:49  cpu: 2%/60% replicas=6
18:38:27  cpu: <unknown>/60% replicas=6
18:38:59  cpu: <unknown>/60% replicas=6
18:39:31  cpu: <unknown>/60% replicas=6
18:40:09  cpu: <unknown>/60% replicas=6
18:40:45  cpu: <unknown>/60% replicas=6
18:41:16  cpu: <unknown>/60% replicas=6
18:41:47  cpu: <unknown>/60% replicas=6
18:42:17  cpu: <unknown>/60% replicas=6
18:42:47  cpu: 7%/60% replicas=2
$ kubectl describe hpa taskboard-backend -n taskboard | grep SuccessfulRescale | sed -E 's/ +/ /g'
 Normal SuccessfulRescale 27m horizontal-pod-autoscaler New size: 4; reason: cpu resource utilization (percentage of request) above target
 Normal SuccessfulRescale 27m horizontal-pod-autoscaler New size: 6; reason: cpu resource utilization (percentage of request) above target
 Normal SuccessfulRescale 20s horizontal-pod-autoscaler New size: 2; reason: All metrics below target
$ kubectl get pods -n taskboard -l app=taskboard-backend
NAME                                READY   STATUS        RESTARTS        AGE
taskboard-backend-fd9cf8b97-72vf9   1/1     Terminating   3 (3m49s ago)   81m
taskboard-backend-fd9cf8b97-bmqlx   1/1     Terminating   3 (3m49s ago)   81m
taskboard-backend-fd9cf8b97-ncvhb   1/1     Terminating   3 (3m49s ago)   27m
taskboard-backend-fd9cf8b97-w7tkm   1/1     Running       2 (3m49s ago)   27m
taskboard-backend-fd9cf8b97-ww2g2   1/1     Running       2 (3m49s ago)   27m
taskboard-backend-fd9cf8b97-zcl7t   1/1     Terminating   3 (3m49s ago)   27m
```

### HPA - second attempt sized for the node

`values-minikube.yaml` caps the local HPA at 4 replicas, and the load generator runs 4 requests in parallel:

![hpa gentle](screenshots/24_hpa_gentle.png)

```
$ # second run, sized for this node: 4 requests in parallel, HPA max 4 (values-minikube.yaml)
$ kubectl get hpa -n taskboard
NAME                REFERENCE                      TARGETS              MINPODS   MAXPODS   REPLICAS   AGE
taskboard-backend   Deployment/taskboard-backend   cpu: <unknown>/60%   2         4         2          96m
$ kubectl run load -n taskboard --restart=Never --image=curlimages/curl --env REQUESTS=14000 --env CONCURRENCY=4 --command -- sh -c "$(cat scripts/load-test.sh)"
pod/load created
$ for i in $(seq 1 12); do sleep 20; printf '%s  ' "$(date +%T)"; kubectl get hpa taskboard-backend -n taskboard --no-headers | awk '{printf "%s %s replicas=%s  ", $3, $4, $7}'; docker stats --no-stream --format 'node CPU={{.CPUPerc}} MEM={{.MemUsage}}' devops; done
18:57:56  cpu: <unknown>/60% replicas=2  node CPU=401.69% MEM=2.295GiB / 2.734GiB
18:58:19  cpu: <unknown>/60% replicas=2  node CPU=368.63% MEM=2.294GiB / 2.734GiB
18:58:40  cpu: <unknown>/60% replicas=2  node CPU=426.05% MEM=2.288GiB / 2.734GiB
18:59:02  cpu: 338%/60% replicas=2  node CPU=308.47% MEM=2.295GiB / 2.734GiB
18:59:24  cpu: 338%/60% replicas=4  node CPU=422.15% MEM=2.368GiB / 2.734GiB
18:59:48  cpu: 338%/60% replicas=4  node CPU=418.27% MEM=2.349GiB / 2.734GiB
19:00:12  cpu: 338%/60% replicas=4  node CPU=428.59% MEM=2.347GiB / 2.734GiB
19:00:37  cpu: <unknown>/60% replicas=4  node CPU=416.27% MEM=2.325GiB / 2.734GiB
19:01:00  cpu: <unknown>/60% replicas=4  node CPU=412.07% MEM=2.381GiB / 2.734GiB
19:01:24  cpu: <unknown>/60% replicas=4  node CPU=415.42% MEM=2.374GiB / 2.734GiB
19:01:46  cpu: <unknown>/60% replicas=4  node CPU=408.23% MEM=2.364GiB / 2.734GiB
19:02:09  cpu: <unknown>/60% replicas=4  node CPU=217.63% MEM=2.38GiB / 2.734GiB

$ kubectl top pods -n taskboard -l app=taskboard-backend
error: Metrics API not available
$ kubectl get pods -n taskboard -l app=taskboard-backend
NAME                                READY   STATUS    RESTARTS   AGE
taskboard-backend-d9474d8fd-gsgmx   1/1     Running   0          5m23s
taskboard-backend-d9474d8fd-mgmrp   1/1     Running   0          6m37s
taskboard-backend-d9474d8fd-mjn26   1/1     Running   0          3m35s
taskboard-backend-d9474d8fd-wf477   1/1     Running   0          3m35s
$ kubectl describe hpa taskboard-backend -n taskboard | grep SuccessfulRescale | tail -2 | sed -E 's/ +/ /g'
 Normal SuccessfulRescale 20m horizontal-pod-autoscaler New size: 2; reason: All metrics below target
 Normal SuccessfulRescale 3m51s horizontal-pod-autoscaler New size: 4; reason: cpu resource utilization (percentage of request) above target
```

2 → 4 replicas, no restarts, the API stayed up. The node's CPU was still saturated (~400%), and
metrics-server lost some readings (`<unknown>`) while it was.

---

Task 7: Monitoring - Prometheus and Grafana
-------------------------------------------

```
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace -f monitoring/prometheus-values.yaml --version 92.1.0
kubectl apply -f monitoring/taskboard-dashboard.yaml
```

![metrics](screenshots/16_metrics.png)

```
$ # port-forwards: backend Service -> :8001, Prometheus -> :9090
$ curl -s localhost:8001/metrics | grep -E '^# TYPE http_request' | head -3
# TYPE http_requests_total counter
# TYPE http_requests_created gauge
# TYPE http_request_size_bytes summary
$ curl -s localhost:8001/metrics | grep -E '^http_requests_total'
http_requests_total{handler="/metrics",method="GET",status="2xx"} 89.0
http_requests_total{handler="/ready",method="GET",status="2xx"} 128.0
http_requests_total{handler="/health",method="GET",status="2xx"} 84.0

$ # the ServiceMonitor the chart created, and the targets Prometheus built from it
$ kubectl get servicemonitor taskboard-backend -n taskboard -o jsonpath='{.spec.selector.matchLabels} port={.spec.endpoints[0].port} path={.spec.endpoints[0].path} every {.spec.endpoints[0].interval}{"\n"}'
{"app":"taskboard-backend"} port=http path=/metrics every 15s
$ q() { curl -s localhost:9090/api/v1/query --data-urlencode "query=$1" | py -c "import json,sys; [print(' '.join(f'{k}={v}' for k,v in r['metric'].items() if k in ('pod','handler','method')) or '{}', '=>', r['value'][1]) for r in json.load(sys.stdin)['data']['result']]"; }
$ q 'up{job="taskboard-backend"}'
pod=taskboard-backend-d9474d8fd-gq7vc => 1
pod=taskboard-backend-d9474d8fd-fscbz => 1
```

The ServiceMonitor selects the backend Service by label `app=taskboard-backend` and scrapes its `http`
port every 15 s; Prometheus turns that into one target per backend pod.

The provisioned Grafana dashboard (ConfigMap with `grafana_dashboard: "1"`, loaded by the sidecar), captured
right after the first HPA test: 6 targets UP, 6 replicas, the request spike at 18:15 and the gap where the
overloaded node could not be scraped. The lower panels had not finished loading when it was captured.

![grafana](screenshots/35_grafana.png)

---

Task 8: Failure simulation and troubleshooting
----------------------------------------------

### Broken image

![broken image](screenshots/20_broken_image.png)

```
$ kubectl apply -f troubleshooting/broken-image.yaml
deployment.apps/taskboard-broken-image created
$ sleep 25; kubectl get pods -n taskboard -l app=broken-image
NAME                                      READY   STATUS             RESTARTS   AGE
taskboard-broken-image-6669966b5b-8dczg   0/1     ImagePullBackOff   0          25s
$ kubectl describe pod -n taskboard -l app=broken-image | sed -n '/^Events/,$p' | sed -E 's/ +/ /g' | cut -c1-150
Events:
 Type Reason Age From Message
 ---- ------ ---- ---- -------
 Normal Scheduled 25s default-scheduler Successfully assigned taskboard/taskboard-broken-image-6669966b5b-8dczg to devops
 Normal BackOff 22s kubelet Back-off pulling image "ghcr.io/example/taskboard-backend:does-not-exist"
 Warning Failed 22s kubelet Error: ImagePullBackOff
 Normal Pulling 11s (x2 over 24s) kubelet Pulling image "ghcr.io/example/taskboard-backend:does-not-exist"
 Warning Failed 10s (x2 over 23s) kubelet Failed to pull image "ghcr.io/example/taskboard-backend:does-not-exist": failed to pull and unpack image "gh
 Warning Failed 10s (x2 over 23s) kubelet Error: ErrImagePull
$ kubectl get events -n taskboard --field-selector reason=Failed -o custom-columns=MSG:.message | grep -m1 'Failed to pull' | grep -oE 'failed to resolve reference.*' | fold -w 150
failed to resolve reference "ghcr.io/example/taskboard-backend:does-not-exist": failed to authorize: failed to fetch anonymous token: unexpected statu
s from GET request to https://ghcr.io/token?scope=repository%3Aexample%2Ftaskboard-backend%3Apull&service=ghcr.io: 403 Forbidden
$ # ghcr.io/example/... does not exist (GHCR answers 403, not 404, for a repository you cannot see)
$ # fix: point the deployment at a tag CI really published
$ kubectl set image deploy/taskboard-broken-image -n taskboard backend=ghcr.io/anshulmohanty/taskboard-backend:2d48b0c3e6ccec8114136e1d84121225cbebb9e2
deployment.apps/taskboard-broken-image image updated
$ sleep 30; kubectl get pods -n taskboard -l app=broken-image
NAME                                      READY   STATUS   RESTARTS      AGE
taskboard-broken-image-68b4cd578d-qp598   0/1     Error    2 (25s ago)   30s

$ # the image pulls now, but the container exits - next layer: its logs
$ kubectl logs -n taskboard deploy/taskboard-broken-image --tail 2 | cut -c1-150
	Is the server running on that host and accepting TCP/IP connections?
(Background on this error at: https://sqlalche.me/e/21/e3q8)
$ # the lab manifest has no DATABASE_URL, so the app falls back to localhost:5432 - inject the real one
$ kubectl set env deploy/taskboard-broken-image -n taskboard DATABASE_URL=postgresql+psycopg://taskboard:taskboard@taskboard-postgres:5432/taskboard
deployment.apps/taskboard-broken-image env updated
$ kubectl rollout status deploy/taskboard-broken-image -n taskboard --timeout=120s | tail -1
deployment "taskboard-broken-image" successfully rolled out
$ sleep 15; kubectl get pods -n taskboard -l app=broken-image
NAME                                     READY   STATUS    RESTARTS   AGE
taskboard-broken-image-cdfb4cc88-shgc2   1/1     Running   0          17s
$ kubectl logs -n taskboard deploy/taskboard-broken-image | grep -E 'Uvicorn running'
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
$ kubectl delete -f troubleshooting/broken-image.yaml
deployment.apps "taskboard-broken-image" deleted from taskboard namespace
```

`ImagePullBackOff` → `describe` shows the image reference → fixing the tag exposed the next layer
(`CrashLoopBackOff`: no `DATABASE_URL`) → `logs` → inject the configuration → Running.

### Broken Service

![broken service](screenshots/21_broken_service.png)

```
$ # a toolbox pod (curl image, sleep 3600) to test Services from inside the cluster
$ kubectl apply -f troubleshooting/broken-service.yaml
service/broken-service created
$ kubectl exec -n taskboard toolbox -- curl -sS -m 5 broken-service:8080/health; echo "curl exit code: $?"
curl: (7) Failed to connect to broken-service:8080 after 1 ms: Could not connect to server
command terminated with exit code 7
curl exit code: 7
$ # the Service exists and has a ClusterIP - but does it have endpoints?
$ kubectl get svc broken-service -n taskboard
NAME             TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
broken-service   ClusterIP   10.108.180.37   <none>        8080/TCP   0s
$ kubectl get endpointslices -n taskboard -l kubernetes.io/service-name=broken-service
NAME                   ADDRESSTYPE   PORTS     ENDPOINTS   AGE
broken-service-pnxhp   IPv4          <unset>   <unset>     0s
$ kubectl get svc broken-service -n taskboard -o jsonpath='selector: {.spec.selector}{"\n"}'
selector: {"app":"label-that-does-not-exist"}
$ kubectl get pods -n taskboard --show-labels | grep -v toolbox | awk '{print $1, $NF}' | column -t
NAME                                 LABELS
taskboard-backend-fd9cf8b97-w7tkm    app=taskboard-backend,pod-template-hash=fd9cf8b97
taskboard-backend-fd9cf8b97-ww2g2    app=taskboard-backend,pod-template-hash=fd9cf8b97
taskboard-frontend-8d88fd487-9gbgv   app=taskboard-frontend,pod-template-hash=8d88fd487
taskboard-frontend-8d88fd487-nhnmv   app=taskboard-frontend,pod-template-hash=8d88fd487
taskboard-postgres-5854dd74cd-khdkq  app=taskboard-postgres,pod-template-hash=5854dd74cd
$ # nothing has app=label-that-does-not-exist -> no endpoints -> no traffic. Point the selector at the backend pods:
$ kubectl patch svc broken-service -n taskboard -p '{"spec":{"selector":{"app":"taskboard-backend"}}}'
service/broken-service patched
$ sleep 3; kubectl get endpointslices -n taskboard -l kubernetes.io/service-name=broken-service
NAME                   ADDRESSTYPE   PORTS   ENDPOINTS                 AGE
broken-service-pnxhp   IPv4          8080    10.244.0.24,10.244.0.25   4s
$ kubectl exec -n taskboard toolbox -- curl -sS -m 5 broken-service:8080/health; echo "curl exit code: $?"
curl: (7) Failed to connect to broken-service:8080 after 1 ms: Could not connect to server
command terminated with exit code 7
curl exit code: 7
$ # endpoints exist now, still refused: the pods listen on 8000 but targetPort is 8080 - a second bug
$ kubectl patch svc broken-service -n taskboard --type=json -p '[{"op":"replace","path":"/spec/ports/0/targetPort","value":8000}]'
service/broken-service patched
$ sleep 3; kubectl get endpointslices -n taskboard -l kubernetes.io/service-name=broken-service
NAME                   ADDRESSTYPE   PORTS   ENDPOINTS                 AGE
broken-service-pnxhp   IPv4          8000    10.244.0.25,10.244.0.24   8s
$ kubectl exec -n taskboard toolbox -- curl -sS -m 5 broken-service:8080/health; echo "  curl exit code: $?"
{"status":"UP"}  curl exit code: 0
$ kubectl delete -f troubleshooting/broken-service.yaml
service "broken-service" deleted from taskboard namespace
```

A Service finds pods only through its label selector, then forwards to `targetPort`. Two independent
bugs, two different symptoms: no endpoints at all (selector) and endpoints that refuse connections (port).

---

What I understood
-----------------

- The point of the capstone is the **path**: a commit becomes tested code, an image tagged with that
  commit, a scanned image, a registry artifact, a Helm release, pods behind an Ingress, autoscaled and
  monitored. `helm history`, the image tag and `git log` all line up.
- Tests are the first gate. A test suite that is broken itself (bug 1) blocks the whole pipeline just as
  much as broken code.
- "Started" is not "ready": Compose `depends_on`, init containers, readiness probes and `/ready` all
  exist because a process can be running before it can do its job.
- A Kubernetes Service, an Ingress and a reverse proxy are only names and selectors; if those names drift
  apart, everything deploys "successfully" and nothing works.
- Trivy's result depends on the day: base images and libraries age into vulnerabilities, and the fix is
  usually an upgrade, not a code change.
- Terraform describes infrastructure as code; `plan` shows exactly what will change before anything does,
  and `destroy` removes it all again.
- The HPA adds pods within seconds but removes them slowly, and it cannot create capacity the node
  does not have.
- Monitoring needs the app's cooperation (`/metrics`) and a way to discover it (ServiceMonitor).
- Troubleshooting is layered: fix one thing (the image), and the next problem (configuration) appears.
  `get` → `describe` → `logs` → `events`, every time.
