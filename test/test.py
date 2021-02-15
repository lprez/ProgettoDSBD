from time import sleep
from requests import get, put, post, delete

host = "http://controller.local"

sp_id = post(host + "/service-providers", data={"name": "test123", "serviceProviderPath": "https://github.com/lprez/ProgettoDSBD/blob/master/test/test.tgz?raw=true"}).text
print("Service provider " + sp_id)
opt_id = post(host + "/service-providers/" + sp_id + "/options", data={"valuesFilePath": "https://raw.githubusercontent.com/lprez/ProgettoDSBD/master/test/values.yaml"}).text
print("Option " + opt_id)

print("Service provider list:")
print(get(host + "/service-providers").text)
print("Option list:")
print(get(host + "/service-providers/" + sp_id + "/options").text)
print("Option description:")
print(get(host + "/service-providers/" + sp_id + "/options/" + opt_id).text)
print(put(host + "/service-providers/" + sp_id + "/options/" + opt_id + "/deploy").text)
sleep(10)
print(delete(host + "/service-providers/" + sp_id + "/options/" + opt_id + "/deploy").text)
