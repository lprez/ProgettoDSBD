import subprocess
import urllib.request
from resources import Resources
import yaml

class OptionInstallException(Exception):
    pass

class Option:
    def __init__(self, oid, service_provider, uri):
        self.oid = oid
        self.service_provider = service_provider
        self.uri = uri
        self.__resources = None
        self.name = self.service_provider.name[:33] + "-" + str(hash(self.service_provider.sid + self.oid))

    def set_resources(self, resources):
        self.__resources = resources

    def get_resources(self):
        if self.__resources is None:
            with urllib.request.urlopen(self.uri) as values_file:
                values = yaml.full_load(values_file)

            install_output = self.__install(["--dry-run", "--debug"])
            install_output = install_output.split("MANIFEST:\n")
            install_output = install_output[1].split("NOTES")[0]
            manifest = yaml.load_all(install_output, Loader=yaml.FullLoader)

            self.__resources = Resources.from_manifest_and_values(manifest, values)

        return self.__resources

    def deploy(self):
        self.__install()

    def delete(self):
        sb = subprocess.run(["helm", "uninstall", self.name], capture_output=True, text=True)
        if sb.returncode != 0:
            raise OptionInstallException("helm uninstall terminato con status code " + str(sb.returncode) + ": " + sb.stderr)

    def __install(self, ext_options=[]):
        options = [ self.name,
                    self.service_provider.uri,
                    "--values",
                    self.uri,
                    *ext_options
        ]
        sb = subprocess.run(["helm", "upgrade", "--install", *options], capture_output=True, text=True)

        if sb.returncode != 0:
            raise OptionInstallException("helm install terminato con status code " + str(sb.returncode) + ": " + sb.stderr)

        return sb.stdout

class ServiceProvider:
    def __init__(self, sid, name, uri):
        self.sid = sid
        self.name = name
        self.uri = uri
