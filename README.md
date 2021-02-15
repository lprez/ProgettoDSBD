# Controller OpenShift/Helm

Lo scopo del progetto è implementare un microservizio che permetta di controllare un cluster OpenShift attraverso una API HTTP.
Il microservizio in questione permette a dei Service Provider di terze parti di registrare le proprie applicazioni presso un database,
specificando diverse varianti (dette _opzioni_) con diversi requisiti,
mentre un servizio gestito dal Network Operator effettuerà il deploy delle opzioni sulla base della _utility_ fornita, usando Helm.

## Struttura dell'applicazione

### _resources_

Le classi Resources e PodResources contengono le informazioni sulla _utility_ e sulla richiesta di risorse di ogni opzione.
In particolare, il metodo statico Resources.from_manifest_and_values permette di creare un oggetto Resources a partire dal manifest
generato da Helm e dal file values.yaml (entrambi già decodificati in un dictionary Python). Tale metodo ricerca i Pod/Deployment nel manifest
con le loro richieste di risorse (CPU e memoria) considerando anche le repliche, come anche i PVC, per poi sommare le risorse di ogni
Pod, mentre la _utility_ viene cercata nel values.yaml.

## _serviceprovider_

ServiceProvider e Option contengono i dati dei service provider e delle opzioni. Option ha inoltre un campo privato che contiene l'oggetto
Resources associato. Questo può essere impostato con il metodo set_resources se le risorse sono già note (ovvero quando la Option è stata
ottenuta dal database), altrimenti verrà creato quando richiesto (alla chiamata di get_resources) lanciando un sottoprocesso Helm che
ottiene il manifest dell'opzione (usando l'opzione --dry-run). Similmente, i metodi deploy e delete utilizzano Helm per fare il deploy
dell'opzione o rimuoverlo.

## _servicestore_

ServiceStore implementa i metodi di accesso al database Neo4j. I nodi nel database sono ServiceProvider, Option e Pod, mentre le relazioni
sono HAS_OPTION tra ServiceProvider e Option, e HAS_POD tra Option e Pod. Le informazioni memorizzate sono gli URL in cui trovare i pacchetti
Helm e file values.yaml, gli identificativi dei Service Provider e Option, e le risorse utilizzate da ogni Option, con un nodo Pod per ogni
pod utilizzato che memorizza le risorse per ogni pod.

## _run_

Implementa la API del microservizio usando Flask, ovvero:
* GET /service-providers: ottiene la lista dei Service Provider (in formato JSON)
* POST /service-providers: aggiunge un Service Provider
* GET /service-providers/:id/options: ottiene la lista delle opzioni relative al Service Provider id
* POST /service-providers/:id/options: aggiunge una opzione al Service Provider id
* GET /service-providers/:id/options/:id2: descrive l'opzione id2 del Service Provider id
* PUT /service-providers/:id/options/:id2/deploy: effettua il deploy dell'opzione id2 del Service Provider id
* DELETE /service-providers/:id/options/:id2/deploy: elimina il deploy dell'opzione id2 del Service Provider id

## Test su Minishift
Inizializzare minishift e impostare le variabili d'ambiente:

    minishift start
    eval $(minishift oc-env)
    eval $(minishift docker-env)
  
Aggiungere il ruolo _cluster-admin_ al service account _builder_, per permettere a Helm di installare applicazioni nel cluster:

    oc login -u system:admin
    oc adm policy add-role-to-user cluster-admin -z builder
  
Build del microservizio:

    docker build -t controller:v1 controller

Deployment del microservizio e neo4j:

    oc create -f k8s/secret.yml
    oc apply -f k8s/db.yaml
    oc apply -f k8s/controller.yaml
  
Creare il Route verso il microservizio:

    oc expose service controller --hostname=controller.local
    echo "$(minishift ip) controller.local" | sudo tee -a /etc/hosts
  
Applicazione test (crea un Service Provider e una opzione, fa il deploy e lo rimuove dopo 10 secondi):

    python test/test.py
