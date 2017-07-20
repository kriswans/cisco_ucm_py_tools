"""Author: Kris Swanson, kriswans@cisco.com """
"""This was originally part of the cisco_ucm_py_tools repository @ https://github.com/kriswans/cisco_ucm_py_tools """
"""Be advised that the AXLAPI.wsdl, AXLEnums.xsd, and AXLSoap.xsd must be in the directory where this script is run  """
"""Please use suds-jurko (pip install suds-jurko), not 'suds' module """


import ssl
import urllib
import os
import time
import datetime
import sys

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



def FindDevNoDN(wsdl, cucm, username, password):

        dev_list=[]
        axl=AXL(username,password,wsdl,cucm)
        resp=axl.client.service.listPhone ({'name': 'CSF%'}, returnedTags={'name': '', 'description': '', 'ownerUserName':''})
        i=0
        len_resp=len(resp[1][0]['phone'])

        while i < len_resp:
            csf_devs=(resp[1][0][0][i]['name'])
            dev_list.append(csf_devs)
            i=i+1

        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d_@_%H.%M.%S')
        fname=('nonum_'+st+'.txt')
        nonum=open(fname,'w')

        for dev in dev_list:
            try:
                get_phone=axl.client.service.getPhone (name= dev)
                DN=get_phone[1][0][0]['lines']['line'][0]['dirn']['pattern']
            except TypeError:
                nonum.write(dev)
                nonum.write('\n')

        nonum.close()

if __name__=="__main__":
    cwd=(os.getcwd())
    print("Looking for AXLAPI.wsdl in current working directory:\n{cwd}\n".format(cwd=cwd))
    orph_list=[]
    orph_dn_list=[]
    wsdl = 'file:///'+cwd+'/AXLAPI.wsdl'
    cucm=input("Please enter the target CUCM address: ")
    username=input("Please enter AXL username: ")
    password=input("Please enter the AXL password: ")

    FindDevNoDN(wsdl,cucm,username,password)
