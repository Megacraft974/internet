import requests
import json
#import pysftp

url = 'http://patrice.atwebpages.com/frigo/index.php?page=addImg'

"""params = {'section':'oracle', 'year':2006}
r = requests.get(url)

print(r.status_code)
print(r.headers)
print(r.text)

formdata = {"ref":"23456","categorie":"Eau","Quantite":"1","Unite":"litre","Stock":"10"}
p = requests.post(url, data=formdata)

print(p.status_code)
print(p.text)"""

barcode ="1246846"
filename="home.png"

file = {barcode:open("C:/Users/willi/iCloudDrive/Python/internet/Frigo/"+filename,"rb").read()}
r = requests.post(url,data=file,auth=('3482246_pat', 'pat/Pat/974'))
"""srv = pysftp.Connection(host="patrice.atwebpages.com", username="3482246_pat",password="pat/Pat/974")
with pysftp.Connection('patrice.atwebpages.com', username='3482246_pat', password='pat/Pat/974') as sftp:
    print(sftp)"""
print(r.status_code)
print(r.text)
