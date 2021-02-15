from neo4j import GraphDatabase
import resources
from serviceprovider import ServiceProvider, Option
from resources import Resources, PodResources

class ServiceNotFoundException(Exception):
    pass

class OptionNotFoundException(Exception):
    pass

class ServiceStore:
    def __init__(self, uri, auth):
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def list_service_providers(self):
        providers = []
        with self.driver.session() as session:
            result = session.run("MATCH (sp:ServiceProvider) RETURN sp.id as id, sp.name as name, sp.serviceProviderPath as uri")
            for record in result:
                providers.append(ServiceProvider(record["id"], record["name"], record["uri"]))
        return providers

    def list_options(self, sid):
        options = []
        with self.driver.session() as session:
            result = session.run(( "MATCH (sp:ServiceProvider {id: $sid}) "
                                   "OPTIONAL MATCH (sp) -[:HAS_OPTION ]-> (opt:Option) "
                                   "RETURN sp, CASE WHEN opt IS NULL THEN [] ELSE collect(opt) END as opts" ),
                                 {"sid": sid})
            for record in result:
                provider = ServiceProvider(
                    record["sp"]["id"],
                    record["sp"]["name"],
                    record["sp"]["serviceProviderPath"]
                )
                for opt in record["opts"]:
                    options.append(
                            (Option(
                                opt["id"],
                                provider,
                                opt["valuesFilePath"]),
                             Resources(
                                opt["utility"],
                                opt["cpu"],
                                opt["memory"],
                                opt["storage"],
                                None))
                    )
                return options

        raise ServiceNotFoundException("Service provider " + str(sid) + " non trovato")

    def get_service_provider(self, sid):
        with self.driver.session() as session:
            result = session.run(( "MATCH (sp:ServiceProvider {id: $sid})"
                                   "RETURN sp.id as id, sp.name as name, sp.serviceProviderPath as uri"),
                                   {"sid": sid})
            for record in result:
                return ServiceProvider(record["id"], record["name"], record["uri"])
        raise ServiceNotFoundException("Service provider " + str(sid) + " non trovato")

    def get_option(self, sid, oid, get_resources=True):
        with self.driver.session() as session:
            if get_resources:
                result = session.run( ( "MATCH (sp:ServiceProvider {id: $sid}) -[:HAS_OPTION]-> (opt:Option {id: $oid}) "
                                        "WITH sp, opt "
                                        "OPTIONAL MATCH (opt) -[:HAS_POD]-> (pod:Pod) "
                                        "RETURN sp as serviceProvider, opt as option, collect(pod) as pods " ),
                                        { "sid": sid, "oid": oid }
                                    )
            else:
                result = session.run( ( "MATCH (sp:ServiceProvider {id: $sid}) -[:HAS_OPTION]-> (opt:Option {id: $oid}) "
                                        "RETURN sp as serviceProvider, opt as option " ),
                                        { "sid": sid, "oid": oid }
                                    )
            found = False
            for record in result:
                found = True
                service_provider = ServiceProvider(sid,
                                                   record["serviceProvider"]["name"],
                                                   record["serviceProvider"]["serviceProviderPath"])
                option = Option(oid, service_provider, record["option"]["valuesFilePath"])

                if get_resources:
                    pods = []
                    for pod in record["pods"]:
                        pods.append(PodResources(
                            pod["ownedBy"],
                            pod["cpu"],
                            pod["memory"],
                            pod["storage"]
                        ))
                    option.set_resources(Resources(
                        record["option"]["utility"],
                        record["option"]["cpu"],
                        record["option"]["memory"],
                        record["option"]["storage"],
                        pods
                    ))
        if found:
            return option
        else:
            raise OptionNotFoundException("Opzione " + str(sid) + "/" + str(oid) + " non trovata")

    def add_service_provider(self, service_provider):
        with self.driver.session() as session:
            session.run( ( "CREATE (sp:ServiceProvider {id: $sid}) "
                           "SET sp.name = $name "
                           "SET sp.serviceProviderPath = $uri " ),
                           { "sid": service_provider.sid,
                             "name": service_provider.name,
                             "uri": service_provider.uri }
                       )

    def add_option(self, option, sid=None):
        resources = option.get_resources()
        pod_maps = [
                { "ownedBy": pod.owned_by,
                  "cpu": pod.cpu,
                  "memory": pod.memory,
                  "storage": pod.storage,
                  "name": pod.owned_by + "-pod-" + str(idx),
                } for idx, pod in enumerate(resources.pods)
        ]

        with self.driver.session() as session:
            session.run(
                    ( "MATCH (sp:ServiceProvider {id: $sid}) "
                      "CREATE (sp) -[:HAS_OPTION]-> (opt:Option {id: $oid}) "
                      "SET opt.valuesFilePath = $uri "
                      "SET opt.cpu = $cpu "
                      "SET opt.memory = $memory "
                      "SET opt.storage = $storage "
                      "SET opt.utility = $utility "
                      "WITH opt "
                      "UNWIND $podlist AS podresources "
                      "CREATE (opt) -[:HAS_POD]-> (pod:Pod) "
                      "SET pod = podresources" ),
                    { "sid": option.service_provider.sid if sid is None else sid,
                      "oid": option.oid,
                      "uri": option.uri,
                      "cpu": resources.cpu,
                      "memory": resources.memory,
                      "storage": resources.storage,
                      "utility": resources.utility,
                      "podlist": pod_maps }
            )


    def close(self):
        self.driver.close()
