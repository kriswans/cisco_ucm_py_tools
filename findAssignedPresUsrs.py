""" version 0.1"""
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
import getpass

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


def presAssgnUsers(wsdl, cucm, username, password):
    """
    This function polls UCM for assigned presence users hten builds lists for users and nodes that they are assigned to.
    It will write 2 time-stamped csv files containing the assigned pres users and assigned user to node mapping.
    It will subsequently ask the user to input a single-column file with a number of users to match zomg the assigned presence users.
    Based on the input file contents it the function will generate match file list those users that are assigned and another for users that do not appear.
    """

    axl=AXL(username,password,wsdl,cucm)

    resp_pres_assg=axl.client.service.listAssignedPresenceUsers({'userid':''},returnedTags={'userid': '', 'server':''})

    len_pres_assg=len(resp_pres_assg[1][0][0])

    i=0
    assg_list=[]
    assg_node=[]
    ts = time.time()
    st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d_@_%H.%M.%S')
    f=open('assg_pres_&_node_'+st+'.csv','w')
    g=open('current_pres_users_'+st+'.csv','w')
    while i < len_pres_assg:
        a=resp_pres_assg[1][0][0][i][1]
        assg_list.append(a)
        f.write(a+', ')
        g.write(a+'\n')
        b=resp_pres_assg[1][0][0][i][2][0]
        assg_node.append(b)
        f.write(b+'\n')
        i+=1
    f.close()
    g.close()

    print("\n\n!! Be sure to include user search file in the same directory as the runing program !!\n\n")
    search_file=input("Type fype filename (including extension) that contains the user to search presence assignment: ")

    g=open(search_file,'r')
    search_list=g.readlines()
    g.close()
    match_list=[]
    match_file=open('user_pres_match_file_'+st+'.csv','w')
    miss_list=[]
    miss_file=open('user_pres_miss_file_'+st+'.csv','w')
    for name in search_list:
        s=name.rstrip('\n')
        if s in assg_list:
            print(s+" is in list")
            match_file.write(s+'\n')
            match_list.append(s)

        if s not in assg_list:
            print(s+" not in list.")
            miss_file.write(s+'\n')
            miss_list.append(s)



if __name__=="__main__":
    cwd=(os.getcwd())
    wsdl = 'file:///'+cwd+'/AXLAPI.wsdl'
    cucm=input("Please enter the target CUCM address: ")
    username=input("Please enter AXL username: ")
    password=getpass.getpass("Please enter the AXL password: ")
    presAssgnUsers(wsdl,cucm,username,password)
