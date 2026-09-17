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

---

Environment
-----------

All commands were run on this machine and every screenshot is the real terminal output of the
command shown above it.

| Layer | What I used |
|---|---|
| Host | Windows 11, Git Bash |
| Linux topics (01-04) | `ubuntu:24.04` container on Docker Desktop, with the repo bind-mounted at `/work` |
| systemd / `journalctl` (01) | A second container started with `/sbin/init` as PID 1, since a normal container has no init system |
| Docker topics (05-07) | Docker Engine 29.5.3 via Docker Desktop |
| Kubernetes topics (08-11) | **minikube v1.37.0**, single node, docker driver, containerd runtime, Kubernetes v1.37.0 |
| Ingress (11) | NGINX ingress controller via `minikube addons enable ingress` |

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

---

Reference
---------

Class repository: https://github.com/Nency-Ravaliya/devops-heros
