from uuid import uuid4
from flask import Flask, jsonify, request
from servicestore import ServiceStore, ServiceNotFoundException, OptionNotFoundException
from serviceprovider import ServiceProvider, Option, OptionInstallException
from resources import OptionParseException

import os
import subprocess
import time
import yaml

app = Flask(__name__)

uri = "neo4j://neo4j:7687"
user, password = auth=os.getenv("NEO4J_AUTH").split("/")

store = ServiceStore(uri, (user, password))

 
@app.route("/service-providers", methods=["GET"])
def get_service_providers():
    providers = store.list_service_providers()
    return jsonify([{
        "name": provider.name,
        "serviceProviderId": provider.sid,
        "serviceProviderPath": provider.uri
        } for provider in providers])

@app.route("/service-providers", methods=["POST"])
def add_service_provider():
    sid = str(uuid4())
    sp = ServiceProvider(sid, request.form["name"], request.form["serviceProviderPath"])
    store.add_service_provider(sp)
    return sid

@app.route("/service-providers/<uuid:sid>/options", methods=["GET"])
def get_options(sid):
    try:
        options = store.list_options(str(sid))
    except ServiceNotFoundException as e:
        abort(404, description=str(e))
    return jsonify([{
        "optionId": opt.oid,
        "cpu": resources.cpu,
        "ram": resources.memory,
        "storage": resources.storage,
        "utility": resources.utility,
        "valuesFilePath": opt.uri,
        } for opt, resources in options])

@app.route("/service-providers/<uuid:sid>/options", methods=["POST"])
def add_option(sid):
    oid = str(uuid4())
    sp = store.get_service_provider(str(sid))
    option = Option(oid, sp, request.form["valuesFilePath"])
    store.add_option(option)
    return oid

@app.route("/service-providers/<uuid:sid>/options/<uuid:oid>", methods=["GET"])
def get_option(sid, oid):
    option = store.get_option(str(sid), str(oid))
    return {
        "optionId": option.oid,
        "cpu": option.get_resources().cpu,
        "ram": option.get_resources().memory,
        "storage": option.get_resources().storage,
        "utility": option.get_resources().utility,
        "valuesFilePath": option.uri,
        "Resources": [
                {
                    "ownedBy": pod.owned_by,
                    "cpu": pod.cpu,
                    "ram": pod.memory,
                    "storage": pod.storage
                } for pod in option.get_resources().pods
            ]
    }

@app.route("/service-providers/<uuid:sid>/options/<uuid:oid>/deploy", methods=["PUT"])
def deploy_option(sid, oid):
    option = store.get_option(str(sid), str(oid), get_resources=False)
    option.deploy()
    return "Deployed " + str(oid)

@app.route("/service-providers/<uuid:sid>/options/<uuid:oid>/deploy", methods=["DELETE"])
def delete_option(sid, oid):
    option = store.get_option(str(sid), str(oid), get_resources=False)
    option.delete()
    return "Deleted " + str(oid)

@app.errorhandler(ServiceNotFoundException)
def handle_service_not_found(e):
    return str(e), 404

@app.errorhandler(OptionNotFoundException)
def handle_option_not_found(e):
    return str(e), 404

@app.errorhandler(OptionInstallException)
def handle_option_install_exception(e):
    return str(e), 500

@app.errorhandler(OptionParseException)
def handle_option_parse_exception(e):
    return str(e), 500
