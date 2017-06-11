"""Author: Kris Swanson, kriswans@cisco.com """
"""This was originally part of the cisco_ucm_py_tools repository @ https://github.com/kriswans/cisco_ucm_py_tools """
"""Be advised that the AXLAPI.wsdl, AXLEnums.xsd, and AXLSoap.xsd must be in the direcotry where this script is run  """


import ssl
import urllib
import os
import time
import datetime

from suds.transport.https import HttpAuthenticated
from suds.client import Client

from suds.xsd.doctor import Import
from suds.xsd.doctor import ImportDoctor


class AXL(object):

    """
    The AXL class sets up the connection to the call manager/UCM with methods for configuring UCM.
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

    """ Create empty lists to fill later.
    These will contain values to be written to csv with ophaned devices and DNs """
    orph_list=[]
    orph_dn_list=[]

    """Creating a couple text files to seperately list ophaned CSFs and DNs """
    orph_CSFs=open('orph_CSFs.txt','w')
    orph_DNs=open('orph_DNs.txt','w')

    """ From the listPhone response we establish the lenth of the tuple to iterate through
     that range"""
    len_resp=len(resp[1][0][0])
    for dev in range (0,len_resp):
        try:
            orph=resp[1][0][0][dev][3][0]
        except IndexError:
            orph=resp[1][0][0][dev][1]
            orph_CSFs.write(orph+'\n')
            orph_list.append(orph)

    """ From the list of phones that has no user associated, we want to pull the DNs. If there is
    no DN associated, it will throw a TypeError and we want to write 'No Number' to our list/csv"""
    for phones in orph_list:
        try:
            get_phone=axl.client.service.getPhone (name= phones)
            DN=get_phone[1][0][0]['lines']['line'][0]['dirn']['pattern']
            orph_DNs.write(DN+'\n')
            orph_dn_list.append(DN)
        except TypeError:
            DN="No Number"
            orph_DNs.write(DN+'\n')
            orph_dn_list.append(DN)

    orph_CSFs.close()
    orph_DNs.close()

    """Create a csv where the name includes the timestamp when the python script was run that
    will contain the orphaned devices and DNs """
    ts = time.time()
    st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d_@_%H.%M.%S')
    orph_matrix=open('orphan_devs_'+st+'.csv','w')

    """Establish the length of the orphan list to iterate through. """
    orph_len=len(orph_list)
    for rows in range(0,orph_len):
        orph_matrix.write(orph_list[rows]+',')
        orph_matrix.write(orph_dn_list[rows]+'\n')

    orph_matrix.close()



if __name__=="__main__":
    cwd=(os.getcwd())
    print("Looking for AXLAPI.wsdl in current working directory:\n{cwd}\n".format(cwd=cwd))
    wsdl = 'file:///'+cwd+'/AXLAPI.wsdl'
    cucm=input("Please enter the target CUCM address: ")
    username=input("Please enter AXL username: ")
    password=input("Please enter the AXL password: ")
    orphanFinder(wsdl,cucm,username,password)
