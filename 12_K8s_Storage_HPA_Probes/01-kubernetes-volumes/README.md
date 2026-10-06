Kubernetes Volumes – What I Learned
===================================

Name: Anshul Mohanty    Roll No: 24BCS10191    Section: A

The hands-on runs of every manifest in this folder, with screenshots, are in
[Task 1 of the topic README](../README.md#task-1-kubernetes-volumes).

A container's filesystem is thrown away when the container restarts. Volumes are how data
outlives a container - and the type of volume decides **how long** it outlives it.

```
container restart  <  Pod deleted  <  node lost  <  cluster storage
   (nothing)          emptyDir        hostPath       PersistentVolume
```

---

emptyDir
--------

An empty directory created when the Pod is scheduled and deleted when the Pod is removed.
It survives a **container** restart inside the Pod, but not the Pod itself.

```yaml
volumes:
  - name: shared-cache
    emptyDir: {}              # or emptyDir: { medium: Memory } for a tmpfs in RAM
```

**Use it for:** sharing files between containers of one Pod (a sidecar reading logs the main
container writes), scratch space, caches.
**Example in this folder:** [emptydir-pod.yaml](emptydir-pod.yaml) - a busybox writer and an nginx
reader sharing one directory.

---

hostPath
--------

Mounts a file or directory from the **node's** filesystem into the Pod.

```yaml
volumes:
  - name: host-storage
    hostPath:
      path: /tmp/hostpath-data
      type: DirectoryOrCreate
```

**Use it for:** node-level agents - log collectors reading `/var/log`, monitoring agents,
anything that genuinely needs to see the node.
**Avoid it for:** application data. A rescheduled Pod on another node sees a different (empty)
directory, and a Pod with hostPath access can read or damage the node's files.
**Example:** [hostpath-pod.yaml](hostpath-pod.yaml).

---

PersistentVolume (PV)
---------------------

A piece of storage in the cluster - a cloud disk, an NFS share, a local path - represented as a
**cluster-scoped** object with a capacity, access modes and a reclaim policy. It exists
independently of any Pod.

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: student-pv
spec:
  storageClassName: ""
  capacity:
    storage: 1Gi
  accessModes: [ReadWriteOnce]
  persistentVolumeReclaimPolicy: Retain
  hostPath:
    path: /tmp/student-data
```

| Access mode | Meaning |
|---|---|
| `ReadWriteOnce` (RWO) | Read-write by Pods on **one node** |
| `ReadOnlyMany` (ROX) | Read-only by many nodes |
| `ReadWriteMany` (RWX) | Read-write by many nodes (NFS, EFS, CephFS) |
| `ReadWriteOncePod` | Read-write by exactly **one Pod** |

| Reclaim policy | What happens when the claim is deleted |
|---|---|
| `Retain` | PV becomes `Released`, data kept, an admin cleans up |
| `Delete` | PV and the underlying disk are deleted |

---

PersistentVolumeClaim (PVC)
---------------------------

A **namespaced request** for storage: "I need 500Mi, RWO". Pods never reference a PV directly -
they reference a claim, and Kubernetes binds the claim to a matching PV.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: student-pvc
spec:
  storageClassName: ""        # bind to an existing PV instead of provisioning one
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 500Mi
```

```yaml
# in the Pod
volumes:
  - name: persistent-storage
    persistentVolumeClaim:
      claimName: student-pvc
```

The split exists so that developers ask for *what* they need (size, access mode) without knowing
*where* it comes from (which disk, which cloud).

**Examples:** [pv.yaml](pv.yaml), [pvc.yaml](pvc.yaml), [pod.yaml](pod.yaml).
[pvc-no-class.yaml](pvc-no-class.yaml) is the version without `storageClassName: ""` - it ignores
`student-pv` and gets a dynamically provisioned volume instead.

Lifecycle: `Available` → `Bound` → (claim deleted) → `Released` (Retain) or deleted (Delete).

---

StorageClass
------------

Describes a **kind** of storage and which provisioner creates it.

```
$ kubectl get storageclass
NAME                 PROVISIONER                RECLAIMPOLICY   VOLUMEBINDINGMODE
standard (default)   k8s.io/minikube-hostpath   Delete          Immediate
```

| Field | Meaning |
|---|---|
| `provisioner` | Who creates the disk - `ebs.csi.aws.com`, `pd.csi.storage.gke.io`, `k8s.io/minikube-hostpath` |
| `reclaimPolicy` | Applied to every PV it creates |
| `volumeBindingMode` | `Immediate`, or `WaitForFirstConsumer` (create the disk only once a Pod is scheduled, in that node's zone) |
| `allowVolumeExpansion` | Whether a PVC can later be resized |
| `(default)` annotation | Used for every PVC that does not name a class |

---

Dynamic provisioning
--------------------

With a StorageClass, nobody creates PVs by hand. A PVC names a class, the provisioner creates a
matching PV named `pvc-<uid>`, and binds it - in about a second on minikube.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: dynamic-pvc
spec:
  storageClassName: standard
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 500Mi
```

```
PVC (500Mi, class=standard)  -->  StorageClass "standard"  -->  provisioner creates PV pvc-6142...  -->  Bound
```

**Example:** [dynamic-pvc.yaml](dynamic-pvc.yaml). Deleting the claim deleted the PV too, because
the class's reclaim policy is `Delete`.

---

Summary
-------

| | emptyDir | hostPath | Static PV + PVC | Dynamic (StorageClass) |
|---|---|---|---|---|
| Lifetime | Pod | Node | Until PV deleted | Until PVC deleted (Delete policy) |
| Who creates storage | Kubelet | Already on node | Admin | Provisioner |
| Survives rescheduling to another node | No | No | Yes (network storage) | Yes |
| Typical use | Sidecar sharing, cache | Node agents | Pre-existing disks | Almost everything in production |
