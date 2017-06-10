import ssl
import urllib
import os

from suds.transport.https import HttpAuthenticated
from suds.client import Client

from suds.xsd.doctor import Import
from suds.xsd.doctor import ImportDoctor


class AXL(object):

    """
    The AXL class sets up the connection to the call manager with methods for configuring UCM.
    Thanks to https://github.com/bobthebutcher, as I reused his class.
    """

    def __init__(self, username, password, wsdl, cucm, cucm_version=10):
        """
        :param username: axl username
        :param password: axl password
        :param wsdl: wsdl file location
        :param cucm: UCM IP address
        :param cucm_version: UCM version
        """
        self.username = username
        self.password = password
        self.wsdl = wsdl
        self.cucm = cucm
        self.cucm_version = cucm_version

        tns = 'http://schemas.cisco.com/ast/soap/'
        imp = Import('http://schemas.xmlsoap.org/soap/encoding/', 'http://schemas.xmlsoap.org/soap/encoding/')
        imp.filter.add(tns)

        t = HttpAuthenticated(username=self.username, password=self.password)
        t.handler = urllib.request.HTTPBasicAuthHandler(t.pm)

        ssl_def_context = ssl.create_default_context()
        ssl_def_context.check_hostname = False
        ssl_def_context.verify_mode = ssl.CERT_NONE

        t1 = urllib.request.HTTPSHandler(context=ssl_def_context)
        t.urlopener = urllib.request.build_opener(t.handler, t1)

        self.client = Client(self.wsdl, location='https://{0}:8443/axl/'.format(cucm), faults=False,
                             plugins=[ImportDoctor(imp)],
                             transport=t)


def orphanFinder(wsdl, cucm, username, password):

    """
    Function to find CSF devices that don't belong to a user, then find the DN associated with the device.
    When users are deleted from the LDAP database, those devices and DNs get orphaned.
    The intent is to feed into other scripts that clean up the devices and DNs, as well as
    recycle the DNs.
    """

    axl=AXL(username,password,wsdl,cucm)

    resp=axl.client.service.listPhone ({'name': 'CSF%'}, returnedTags={'name': '', 'description': '', 'ownerUserName':''})

    len_resp=len(resp[1][0][0])
    orph_list=[]
    orph_dn_list=[]
    orph_CSFs=open('orph_CSFs.csv','w')
    orph_DNs=open('orph_DNs.csv','w')
    for dev in range (0,len_resp):

        try:
            resp[1][0][0][dev][3][0]
        except IndexError:
            orph=resp[1][0][0][dev][1]
            orph_CSFs.write(orph+'\n')
            orph_list.append(orph)

    print (orph_list)

    for phones in orph_list:
        try:
            get_phone=resp=axl.client.service.getPhone (name= phones)
            DN=get_phone[1][0][0]['lines']['line'][0]['dirn']['pattern']
            orph_DNs.write(DN+'\n')
            orph_dn_list.append(DN)
        except TypeError:
            DN="No Number"
            orph_DNs.write(DN+'\n')
            orph_dn_list.append(DN)

    print(orph_dn_list)

if __name__=="__main__":
    cwd=(os.getcwd())
    print("Looking for AXLAPI.wsdl in current working directory:\n{cwd}\n".format(cwd=cwd))
    wsdl = 'file:///'+cwd+'/AXLAPI.wsdl'
    cucm= input("Please enter the target CUCM address: ")
    username= input("Please enter AXL username: ")
    password=input("Please enter the AXL password: ")
    orphanFinder(wsdl,cucm,username,password)
