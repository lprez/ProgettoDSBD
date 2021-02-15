class OptionParseException(Exception):
    pass

class PodResources:
    def __init__(self, owned_by, cpu, memory, storage):
        self.owned_by = owned_by
        self.cpu = cpu
        self.memory = memory
        self.storage = storage

    def from_containers(owned_by, containers):
        pod_res = PodResources(owned_by, 0, 0, 0)
        for spec in containers:
            if ("resources" not in spec or "requests" not in spec["resources"] or
                    "memory" not in spec["resources"]["requests"] or
                    "cpu" not in spec["resources"]["requests"]):
                raise OptionParseException("Risorse richieste non specificate per il container " + spec["name"])

            pod_res.cpu += cpu_to_float(spec["resources"]["requests"]["cpu"])
            pod_res.memory += mem_to_float(spec["resources"]["requests"]["memory"])
        return pod_res

    def from_pod_spec(owned_by, spec, pvcs):
        pod_resource = PodResources.from_containers(owned_by, spec["containers"])
        if "volumes" in spec:
            for volume in spec["volumes"]:
                if "persistentVolumeClaim" in volume:
                    claimName = volume["persistentVolumeClaim"]["claimName"]
                    if claimName in pvcs:
                        pod_resource.storage += pvcs[claimName]
        return pod_resource

    def from_deployment_spec(name, spec, pvcs):
        replicas = spec["replicas"] if "replicas" in spec else 1
        pod_resources = []
        for replica in range(0, replicas):
            pod_resources.append(PodResources.from_pod_spec(name, spec["template"]["spec"], pvcs))
        return pod_resources

    def from_statefulset_spec(name, spec, pvcs):
        pod_resources = PodResources.from_deployment_spec(name, spec, pvcs)
        if "volumeClaimTemplates" in spec:
            for pod_resources in pod_resource:
                pod_resource.storage += mem_to_float(res["spec"]["resources"]["requests"]["storage"])

class Resources:
    def __init__(self, utility, cpu, memory, storage, pods):
        self.utility = utility
        self.cpu = cpu
        self.memory = memory
        self.storage = storage
        self.pods = pods

    def from_manifest_and_values(manifest, values):
        cpu = 0
        memory = 0
        storage = 0

        if "utility" in values:
            utility = values["utility"]
        else:
            raise OptionParseException("Utility non specificata nel file values.yml")

        pods = []
        deployments = []
        statefulsets = []
        pvcs = {}

        for res in manifest:
            if res["kind"] == "Pod":
                pods.append((res["metadata"]["name"], res["spec"]))
            elif res["kind"] == "Deployment":
                deployments.append((res["metadata"]["name"], res["spec"]))
            elif res["kind"] == "StatefulSet":
                statefulsets.append((res["metadata"]["name"], res["spec"]))
            elif res["kind"] == "PersistentVolumeClaim":
                pvcs[res["metadata"]["name"]] = mem_to_float(
                        res["spec"]["resources"]["requests"]["storage"])

        pod_resources = [PodResources.from_pod_spec(name, spec, pvcs) for name, spec in pods]
        for ps in [PodResources.from_deployment_spec(name, spec, pvcs) for name, spec in deployments]:
            pod_resources.extend(ps)
        for ps in [PodResources.from_statefulset_spec(name, spec, pvcs) for name, spec in statefulsets]:
            pod_resources.extend(ps)

        for pod_resource in pod_resources:
            cpu += pod_resource.cpu
            memory += pod_resource.memory
            storage += pod_resource.storage

        return Resources(utility, cpu, memory, storage, pod_resources)

def cpu_to_float(cpu):
    if str(cpu).endswith("m"):
        return float(cpu[:-1]) / 1000
    else:
        return float(cpu)

suffix_multiplier = {
        "K": 10**3,
        "M": 10**6,
        "G": 10**9,
        "T": 10**12,
        "P": 10**15,
        "E": 10**18,
        "Ki": 2**10,
        "Mi": 2**20,
        "Gi": 2**30,
        "Ti": 2**40,
        "Pi": 2**50,
        "Ei": 2**60
}

def mem_to_float(mem):
    mem = str(mem)
    suffix = mem.lstrip('0123456789e-.')
    return float(mem[:-len(suffix)]) * suffix_multiplier[suffix]
