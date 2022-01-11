#!/usr/bin/python3
#Juan Hernandez Sanchez


import sys, os, json
import subprocess
from lxml import etree


def NetworkFileConf(name, pos) :
    subprocess.run(["touch", "hostname"])
    fout = open("hostname",'w')
    fout.write(name + "\n")
    fout.close()
    subprocess.run(["sudo", "virt-copy-in", "-a", name + ".qcow2", "hostname", "/etc"])
    subprocess.run(["rm", "-f", "hostname"])
    
    subprocess.run(["touch", "hosts"])
    fout = open("hosts",'w')
    fout.write("127.0.1.1 " + name + "\n")
    fout.close()
    subprocess.run(["sudo", "virt-copy-in", "-a", name + ".qcow2", "hosts", "/etc"])
    subprocess.run(["rm", "-f", "hosts"])

    subprocess.run(["touch", "interfaces"])
    fout = open("interfaces",'w')
    if pos != -1 :
        fout.write("auto lo eth0\niface lo inet loopback\n\niface eth0 inet static\naddress 10.0.2.1" + str(pos) +"\nnetmask 255.255.255.0 \ngateway 10.0.2.1\n")
    if name == "lb":
        fout.write("auto lo eth0 eth1\niface lo inet loopback\n\niface eth0 inet static\naddress 10.0.1.1\nnetmask 255.255.255.0\niface eth1 inet static\naddress 10.0.2.1\nnetmask 255.255.255.0\n")
    if name == "c1":
        fout.write("auto lo eth0\niface lo inet loopback\n\niface eth0 inet static\naddress 10.0.1.2\nnetmask 255.255.255.0 \ngateway 10.0.1.1\n")
    fout.close()
    subprocess.run(["sudo", "virt-copy-in", "-a", name + ".qcow2", "interfaces", "/etc/network"])
    subprocess.run(["rm", "-f", "interfaces"])

    if name == "lb":
        subprocess.run(["touch", "sysctl.conf"])
        fout = open("sysctl.conf",'w')
        fout.write("net.ipv4.ip_forward=1\n")
        fout.close()
        subprocess.run(["sudo", "virt-copy-in", "-a", "lb.qcow2", "sysctl.conf", "/etc"])
        subprocess.run(["rm", "-f", "sysctl.conf"])



def HAPproxyConf(servers) :
    subprocess.run(["sudo", "virt-copy-out", "-a", os.getcwd() + "/lb" + ".qcow2", "/etc/haproxy/haproxy.cfg", os.getcwd() + "/."])
    subprocess.run(["mv", "haproxy.cfg", "tmp.cfg"])
    fin = open("tmp.cfg", "r")
    fout = open("haproxy.cfg", "w")
    for line in fin:
        fout.write(line)
    fout.write("\nfrontend lb\n")
    fout.write("        bind *:80\n")
    fout.write("        mode http\n")
    fout.write("        default_backend webservers\n\n")
    fout.write("backend webservers\n")
    fout.write("        mode http\n")
    fout.write("        balance roundrobin\n")
    for i in range(servers) :
        fout.write("        server s"+str(i)+" 10.0.2.1" + str(i + 1) + ":80" + " check\n")
    fin.close()
    fout.close()
    subprocess.run(["rm", "-f","./tmp.cfg"])
    subprocess.run(["sudo", "virt-copy-in", "-a", os.getcwd() + "/lb" + ".qcow2", os.getcwd() + "/haproxy.cfg", "/etc/haproxy/"])




if ((len(sys.argv) < 2) or (len(sys.argv) > 3)):
    sys.exit("Command error\nuse \"auto-p2 <orden> <otros_parámetros>\"")

command = sys.argv[1]
servers = 3;
path = os.getcwd()

if (command != "prepare" and command != "launch" and command != "stop" and command != "release"):
        sys.exit("Command error\n<orden> can only be prepare, launch, stop or release")
if (command == "prepare"):
    if(len(sys.argv) == 3):
        if (int(sys.argv[2]) < 1 or int(sys.argv[2]) > 5):
            sys.exit("Command error\nEl número de servidores debe estar entre 1 y 5")
        else:
            servers = int(sys.argv[2])
    data = { "num_serv": servers }
    with open('auto-p2.json', 'w') as outfile:
        json.dump(data, outfile)
    for i in range(servers):
        nameqcow = "s" + str(i + 1) + ".qcow2"
        namexml = "s" + str(i + 1) + ".xml"
        subprocess.run(["qemu-img", "create", "-f", "qcow2" ,"-b" ,"cdps-vm-base-p2.qcow2", nameqcow])
        subprocess.run(["cp", "plantilla-vm-p2.xml", namexml])
        tree = etree.parse(path + "/s" + str(i + 1) + ".xml")
        root = tree.getroot()
        name = root.find("name")
        name.text = "s" + str(i + 1)
        sourceFile = root.find("./devices/disk/source")
        sourceFile.set("file", path + "/" + nameqcow)
        bridge = root.find("./devices/interface/source")
        bridge.set("bridge", "LAN2")
        fout = open(path + "/s" + str(i + 1) + ".xml", "w")
        fout.write(etree.tounicode(tree, pretty_print = True))
        fout.close()
       


    subprocess.run(["qemu-img", "create", "-f", "qcow2" ,"-b" ,"cdps-vm-base-p2.qcow2", "lb.qcow2"])
    subprocess.run(["qemu-img", "create", "-f", "qcow2" ,"-b" ,"cdps-vm-base-p2.qcow2", "c1.qcow2"])
    subprocess.run(["cp", "plantilla-vm-p2.xml", "lb.xml"])
    subprocess.run(["cp", "plantilla-vm-p2.xml", "c1.xml"])

    tree = etree.parse(path + "/c1.xml")
    root = tree.getroot()
    name = root.find("name")
    name.text = "c1"
    sourceFile = root.find("./devices/disk/source")
    sourceFile.set("file", path + "/c1.qcow2")
    bridge = root.find("./devices/interface/source")
    bridge.set("bridge", "LAN1")
    fout = open(path + "/c1.xml", "w")
    fout.write(etree.tounicode(tree, pretty_print = True))
    fout.close()

    tree = etree.parse(path + "/lb.xml")
    root = tree.getroot()
    name = root.find("name")
    name.text = "lb"
    sourceFile = root.find("./devices/disk/source")
    sourceFile.set("file", path + "/lb.qcow2")
    bridge = root.find("./devices/interface/source")
    bridge.set("bridge", "LAN1")
    fout = open(path + "/lb.xml", "w")
    fout.write(etree.tounicode(tree, pretty_print = True))
    fout.close()

    fin = open(path + "/lb.xml",'r')
    fout = open("aux.xml",'w')
    for line in fin:
        if "</interface>" in line:
            fout.write("</interface>\n <interface type='bridge'>\n <source bridge='"+"LAN2"+"'/>\n <model type='virtio'/>\n </interface>\n")
        else:
            fout.write(line)
    fin.close()
    fout.close()
    subprocess.run(["cp","./aux.xml", "./lb.xml"])
    subprocess.run(["rm", "-f", "./aux.xml"])

    subprocess.run(["sudo", "brctl", "addbr", "LAN1"])
    subprocess.run(["sudo", "brctl", "addbr", "LAN2"])
    subprocess.run(["sudo", "ifconfig", "LAN1", "up"])
    subprocess.run(["sudo", "ifconfig", "LAN2", "up"])

    subprocess.run(["sudo", "virsh", "define", "c1.xml"])
    subprocess.run(["sudo", "virsh", "define", "lb.xml"])
    for i in range(servers):
        subprocess.run(["sudo", "virsh", "define", "s" + str(i + 1) + ".xml"])
    
    for i in range(servers):
        NetworkFileConf("s" + str(i + 1), i + 1)
    NetworkFileConf("lb", -1)
    NetworkFileConf("c1", -1)

    subprocess.run(["sudo", "ifconfig", "LAN1", "10.0.1.3/24"])
    subprocess.run(["sudo", "ip", "route", "add", "10.0.0.0/16", "via", "10.0.1.1"])

    HAPproxyConf(servers)

    sys.exit("Success")

else:
    if(len(sys.argv) != 2):
        sys.exit("Command error\nuse \"auto-p2 <orden> <otros_parámetros>\"")


    if (command == "launch"):
        with open('auto-p2.json') as f:
            data = json.load(f)
            servers = int(data["num_serv"])

        subprocess.run(["sudo", "virsh", "start", "lb"])
        subprocess.run(["sudo", "virsh", "start", "c1"])
        os.system("xterm -e 'sudo virsh console lb' &")
        os.system("xterm -e 'sudo virsh console c1' &")
        for i in range(servers):
            subprocess.run(["sudo", "virsh", "start", "s" + str(i + 1)])
            os.system("xterm -e 'sudo virsh console s" + str(i + 1) + "' &")
        sys.exit("Success")
        
            
        
    if (command == "stop"):
        with open('auto-p2.json') as f:
            data = json.load(f)
            servers = int(data["num_serv"])
        for i in range(servers):
            subprocess.run(["sudo", "virsh", "shutdown", "s" + str(i + 1)])
        subprocess.run(["sudo", "virsh", "shutdown", "lb"])
        subprocess.run(["sudo", "virsh", "shutdown", "c1"])
        sys.exit("Success")


    if (command == "release"):
        with open('auto-p2.json') as f:
            data = json.load(f)
            servers = int(data["num_serv"])
        for i in range(servers):
            subprocess.run(["sudo", "virsh", "destroy", "s" + str(i + 1)])
            subprocess.run(["sudo", "virsh", "undefine", "s" + str(i + 1)])
            subprocess.run(["rm", "-f", "s" + str(i + 1) + ".qcow2"])
            subprocess.run(["rm", "-f", "s" + str(i + 1) + ".xml"])
        subprocess.run(["sudo", "virsh", "destroy", "lb"])
        subprocess.run(["sudo", "virsh", "destroy", "c1"])
        subprocess.run(["sudo", "virsh", "undefine", "lb"])
        subprocess.run(["sudo", "virsh", "undefine", "c1"])
        subprocess.run(["rm", "lb.xml"])
        subprocess.run(["rm", "c1.xml"])
        subprocess.run(["rm", "-f", "lb.qcow2"])
        subprocess.run(["rm", "-f", "c1.qcow2"])

        sys.exit("Success")
        

