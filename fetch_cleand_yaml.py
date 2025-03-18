import yaml
import subprocess
import os
import sys

RESOURCE_TYPES = ["deployment", "service", "ingress", "configMap", "hpa"]

def get_k8s_yaml(resource, name, namespace):
    try:
        result = subprocess.run(
            ["kubectl", "get", resource, name, "-n", namespace, "-o", "yaml"],
            capture_output=True, text=True, check=True
        )
        return yaml.safe_load(result.stdout)
    except subprocess.CalledProcessError:
        return None

def get_all_services(namespace):
    try:
        result = subprocess.run(
            ["kubectl", "get", "service", "-n", namespace, "-o", "jsonpath={.items[*].metadata.name}"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.split()
    except subprocess.CalledProcessError:
        return []

def clean_labels(labels):
    return {k: v for k, v in labels.items() if k == "app"}

def clean_k8s_yaml(k8s_yaml):
    if not k8s_yaml:
        return None

    cleaned_yaml = {
        "apiVersion": k8s_yaml["apiVersion"],
        "kind": k8s_yaml["kind"],
        "metadata": {
            "name": k8s_yaml["metadata"]["name"],
            "namespace": k8s_yaml["metadata"].get("namespace", "")
        }
    }

    if k8s_yaml["kind"] in ["Deployment"]:
        cleaned_yaml["spec"] = {
            "replicas": k8s_yaml["spec"]["replicas"],
            "selector": {
                "matchLabels": clean_labels(k8s_yaml["spec"]["selector"]["matchLabels"])
            },
            #"serviceName": k8s_yaml["spec"].get("serviceName", {}),
            "template": {
                "metadata": {
                    "labels": clean_labels(k8s_yaml["spec"]["template"]["metadata"]["labels"])
                },
                "spec": {
                    "volumes": k8s_yaml["spec"]["template"]["spec"].get("volumes", []),
                    "containers": []
                }
            },
            #"volumeClaimTemplates": k8s_yaml["spec"].get("volumeClaimTemplates", {}),
        }

        for container in k8s_yaml["spec"]["template"]["spec"].get("containers", []):
            image_name = container["image"].split(":")[0]
            parameterized_image = f"{image_name}:{{IMAGE_TAG}}"

            cleaned_container = {
                "name": container["name"],
                "image": parameterized_image,
                "imagePullPolicy": container.get("imagePullPolicy", ""),
                "ports": container.get("ports", []),
                "resources": container.get("resources", {}),
                #"volumeMounts": container.get("volumeMounts", []),
                "env": container.get("env", []),
            }

            # Add probes only if they exist
            if "livenessProbe" in container:
                cleaned_container["livenessProbe"] = container["livenessProbe"]
            if "readinessProbe" in container:
                cleaned_container["readinessProbe"] = container["readinessProbe"]

            cleaned_yaml["spec"]["template"]["spec"]["containers"].append(cleaned_container)

    elif k8s_yaml["kind"] == "Service":
        cleaned_yaml["spec"] = {
            "type": k8s_yaml["spec"].get("type", ""),
            "ports": [{"name": p.get("name", None), "port": p["port"], "targetPort": p.get("targetPort", None)} for p in k8s_yaml["spec"].get("ports", [])],
        }
        if "selector" in k8s_yaml["spec"] and "app" in k8s_yaml["spec"]["selector"]:
            cleaned_yaml["spec"]["selector"] = {"app": k8s_yaml["spec"]["selector"]["app"]}

    elif k8s_yaml["kind"] == "HorizontalPodAutoscaler":
        cleaned_yaml["spec"] = {
            "maxReplicas": k8s_yaml["spec"].get("maxReplicas", 1),
            "minReplicas": k8s_yaml["spec"].get("minReplicas", 1),
            "scaleTargetRef": k8s_yaml["spec"].get("scaleTargetRef", {}),
            "metrics": k8s_yaml["spec"].get("metrics", {}),
        }

    elif k8s_yaml["kind"] == "Ingress":
        cleaned_yaml["spec"] = {
            "rules": k8s_yaml["spec"].get("rules", {}),
            "tls": k8s_yaml["spec"].get("tls", {}),
        }

    elif k8s_yaml["kind"] == "ConfigMap":
        cleaned_yaml["data"] = k8s_yaml.get("data", {})

    elif "spec" in k8s_yaml:
        cleaned_yaml["spec"] = k8s_yaml["spec"]

    return cleaned_yaml

def save_yaml_to_file(data, filename):
    class CustomDumper(yaml.SafeDumper):
        def represent_scalar(self, tag, value, style=None):
            if '\n' in value:
                style = '|'
            return super().represent_scalar(tag, value, style)

    with open(filename, "w") as file:
        yaml.dump(data, file, default_flow_style=False, allow_unicode=True, Dumper=CustomDumper)
    print(f"Cleaned YAML saved to {filename}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test1.py <namespace>")
        sys.exit(1)

    namespace = sys.argv[1]
    services = get_all_services(namespace)

    if not services:
        print(f"No services found in namespace {namespace}.")
        return

    for service_name in services:
        output_dir = f"cleaned_yaml/{service_name}"
        os.makedirs(output_dir, exist_ok=True)

        all_cleaned_yaml = {"items": []}

        for resource in RESOURCE_TYPES:
            print(f"Fetching {resource} for service {service_name}...")
            raw_yaml = get_k8s_yaml(resource, service_name, namespace)
            cleaned_yaml = clean_k8s_yaml(raw_yaml)

            if cleaned_yaml:
                filename = f"{output_dir}/{resource}.yaml"
                save_yaml_to_file(cleaned_yaml, filename)
                all_cleaned_yaml["items"].append(cleaned_yaml)

        #merged_filename = f"{output_dir}/{service_name}_all.yaml"
        #save_yaml_to_file(all_cleaned_yaml, merged_filename)

if __name__ == "__main__":
    main()
