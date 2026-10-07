DevOps Assignment
=================

**Name:** Anshul Mohanty
**Roll No:** 24BCS10191
**Section:** A

Every topic has its own folder with a `README.md` containing the commands I ran, screenshots
of the terminal output, the same output as text, and what I understood from it.

---

Contents
--------

| # | Topic | Covers | Learning |
|---|---|---|---|
| 01 | [Linux Fundamentals](01_Linux_Fundamental/README.md) | Hard vs soft links, `useradd` vs `adduser`, `journalctl`, command reference | [notes](01_Linux_Fundamental/LEARNING.md) |
| 02 | [Shell Scripting](02_shell_scripting/README.md) | System information script - variables, `read`, redirection | [notes](02_shell_scripting/LEARNING.md) |
| 03 | [Networking](03_networking/README.md) | IP addressing and subnetting, interfaces, DNS, connectivity, ports | [notes](03_networking/LEARNING.md) |
| 04 | [Git and GitHub](04_git/README.md) | Init, commits, branching, merging, conflict resolution | [notes](04_git/LEARNING.md) |
| 05 | [Docker Fundamentals](05_Docker_Fundamental/README.md) | Images vs containers, run/ps/exec/logs/inspect, lifecycle | [notes](05_Docker_Fundamental/LEARNING.md) |
| 06 | [Dockerfiles and Images](06_DockerFiles_Images/README.md) | Multi-stage builds, image size, six application types | [notes](06_DockerFiles_Images/LEARNING.md) |
| 07 | [Docker Networking and Volumes](07_Docker_Networking/README.md) | bridge/host/none, container DNS, volume persistence | [notes](07_Docker_Networking/LEARNING.md) |
| 08 | [Kubernetes Fundamentals](08_Kubernetes_Fundamentals/README.md) | Cluster architecture, control plane components, namespaces | [notes](08_Kubernetes_Fundamentals/LEARNING.md) |
| 09 | [Pods, ReplicaSets, Deployments](09_K8s_Pods_ReplicaSets_Deployments/README.md) | Self-healing, rolling updates, rollback, DaemonSets, taints | [notes](09_K8s_Pods_ReplicaSets_Deployments/LEARNING.md) |
| 10 | [Kubernetes Services](10_K8s_Networking_Services/README.md) | ClusterIP, NodePort, LoadBalancer, ExternalName, headless, DNS | [notes](10_K8s_Networking_Services/LEARNING.md) |
| 11 | [Ingress, ConfigMaps, Secrets](11_K8s_Ingress_ConfigMaps_Secrets/README.md) | Config injection, base64 secrets, host/path routing | [notes](11_K8s_Ingress_ConfigMaps_Secrets/LEARNING.md) |
| 12 | [Storage, HPA, Probes](12_K8s_Storage_HPA_Probes/README.md) | Volumes, PV/PVC, StorageClass, HPA under load, liveness/readiness/startup, mini project | [notes](12_K8s_Storage_HPA_Probes/LEARNING.md) |
| 13 | [Kubernetes Troubleshooting](13_K8s_Troubleshooting/README.md) | get/describe/logs/exec/events/explain/top, nine broken scenarios fixed, mini project | [notes](13_K8s_Troubleshooting/LEARNING.md) |
| 14 | [Helm](14_Helm/README.md) | Chart from `helm create`, all core commands, upgrade/rollback workflow, notes-chart mini project | [notes](14_Helm/LEARNING.md) |
| 15 | [CI/CD and GitHub Actions](15_GitHub_Actions_CICD/README.md) | Matrix tests, artifacts, Docker build, secrets, publish to GHCR, deploy + verify | [notes](15_GitHub_Actions_CICD/LEARNING.md) |
| 16 | [DevSecOps](16_DevSecOps/README.md) | Bandit/CodeQL, pip-audit, gitleaks, Trivy, security gate, deploy to Kubernetes | [notes](16_DevSecOps/LEARNING.md) |
| 17 | [Terraform and IaC](17_Terraform_IaC/README.md) | S3 demo through the full Terraform workflow, IAM/EC2/S3/VPC/DynamoDB/RDS write-ups | [notes](17_Terraform_IaC/LEARNING.md) |
| 18 | [Cloud and Terraform in Action](18_Cloud_Terraform/README.md) | VPC, subnets, IGW, SG, EC2, IAM, S3 - dependencies, state, plan/apply/destroy | [notes](18_Cloud_Terraform/LEARNING.md) |
| 19 | [Monitoring, Observability, GitOps](19_Monitoring_Observability_GitOps/README.md) | Prometheus, alerts, Grafana, Loki, Jaeger traces; Argo CD sync, self-heal, prune | [notes](19_Monitoring_Observability_GitOps/LEARNING.md) |
| 20 | [Capstone demo: TaskBoard](20_Capstone_TaskBoard/README.md) | FastAPI + React + PostgreSQL through pytest, Docker, Trivy, GHCR, Terraform (VPC + EKS), Helm, Ingress, HPA, Prometheus/Grafana, troubleshooting | [notes](20_Capstone_TaskBoard/LEARNING.md) |

---

Environment
-----------

All commands were run on this machine and every terminal screenshot is the real output of the
command shown above it. Topics 15-19 also include screenshots of web UIs (GitHub Actions runs,
GHCR, Prometheus, Grafana, Jaeger, Argo CD), taken from the running systems.

| Layer | What I used |
|---|---|
| Host | Windows 11, Git Bash |
| Linux topics (01-04) | `ubuntu:24.04` container on Docker Desktop, with the repo bind-mounted at `/work` |
| systemd / `journalctl` (01) | A second container started with `/sbin/init` as PID 1, since a normal container has no init system |
| Docker topics (05-07) | Docker Engine 29.5.3 via Docker Desktop |
| Kubernetes topics (08-11) | **minikube v1.37.0**, single node, docker driver, containerd runtime, Kubernetes v1.37.0 |
| Ingress (11) | NGINX ingress controller via `minikube addons enable ingress` |
| Kubernetes topics (12-14, 16, 19, 20) | **minikube v1.39.0**, profile `devops`, Kubernetes v1.37.0, metrics-server addon |
| Helm (14) | Helm v4.1.4 |
| CI/CD (15-16, 20) | GitHub Actions on this repository (`.github/workflows/`), images published to GHCR |
| Security tools (16) | Bandit 1.9.4, pip-audit 2.10.1, gitleaks 8.30.1, Trivy 0.75.0, CodeQL |
| Terraform (17-18, 20) | Terraform 1.16.5, AWS provider 6.67.0 (5.100 in 20, required by the EKS module), **LocalStack 4.14** as the AWS endpoint |
| Observability (19) | Prometheus 3.15, Grafana 13.2, Loki 3.7, Alloy 1.20, Jaeger 2.21, node-exporter, cAdvisor (Docker Compose) |
| GitOps (19) | Argo CD v3.5.3 on minikube, syncing a folder of this repository |

Kubernetes objects were created in a dedicated `devops-hw` namespace.

### Where my setup differs from a standard one

These are noted in the relevant topic READMEs rather than glossed over, because they change
what the output looks like:

- **Single-node cluster.** minikube removes the `NoSchedule` taint from the control-plane
  node, so the DaemonSet scheduling behaviour in topic 09 does not appear on its own. I
  applied the taint manually to demonstrate it properly.
- **NodePort is not reachable from Windows.** With the docker driver the node IP
  `192.168.49.2` lives inside Docker's Linux VM and Windows has no route to it, so
  `minikube service --url` or `minikube ssh` is needed. Covered in topics 10 and 11.
- **`LoadBalancer` stays `<pending>`.** There is no cloud provider to fulfil it locally. This
  is expected, not a failure.
- **Multi-stage builds saved only 6 MB** on the given example app. I measured it, explained
  why, and added a second example where the pattern actually pays off (311 MB → 102 MB).
- **A new minikube profile from topic 12 on.** After minikube was upgraded from 1.37 to 1.39 the
  old cluster's control plane would not start again (its `/etc/kubernetes` was empty), so topics
  12 onward use a fresh profile named `devops`. That is why the node is called `devops` in those
  outputs; the Kubernetes version is the same.
- **No AWS account - LocalStack instead (17-18).** The Terraform code is ordinary AWS code using
  the real `hashicorp/aws` provider; only the endpoint points at LocalStack running in Docker. One
  variable (`use_localstack = false`) switches it to real AWS. The current LocalStack image needs
  an account token, so it is pinned to 4.14, the last community release. LocalStack does not
  emulate RDS, and its EC2 instances are API mocks that never boot.
- **GitHub Actions evidence (15-16).** The workflows ran on this repository, and the screenshots
  are of the public run and job pages. GitHub only shows job *log lines* to signed-in users, so
  where a log matters the same command or script was also run locally and shown as terminal
  output. Deliberately failing runs were made on separate `ci-demo/...` branches so `main` never
  carried the broken code.

---

Reference
---------

Class repository: https://github.com/Nency-Ravaliya/devops-heros
