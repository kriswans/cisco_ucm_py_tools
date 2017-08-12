""" version 0.3.1"""
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



def orphanFinder(wsdl, cucm, username, password, orph_list, orph_dn_list):

    """
    Function to find CSF devices that don't belong to a user, then find the DN associated with the device.
    When users are deleted from the LDAP database, those devices and DNs get orphaned.
    The intent is to feed into other scripts that clean up the devices and DNs, as well as
    recycle the DNs.
    """
    """
     variables:
     orph_list- list of orphaned devices generated by running orphanFinder function, orphanFinder function usually passed an empty list to populate
     orph_dn_list- list of orphaned DNs associated with each device in orph_list, orphanFinderfunction usually passed an empty list to populate
    """

    axl=AXL(username,password,wsdl,cucm)

    dev_search=str(input("\n\nWould you like to FIND only ophaned devices starting with 'CSF...'(C) or ALL Orphaned devices(A)? (Enter C or A): "))

    if dev_search == 'C':
        dev_prefix='CSF%'
        print("\n\nSearching CSF orphaned devices")
    elif dev_search == 'A':
        dev_prefix='%'
        print("\n\nSearching ALL orphaned devices")
    else:
        print("\n\nIncorrect input. Exiting...\n\n")
        sys.exit()

    try:
        resp=axl.client.service.listPhone ({'name': dev_prefix}, returnedTags={'name': '', 'description': '', 'ownerUserName':''})
    except:
        print("\n\nThere was an issue connecting to UCM. Check IP/Name. Exiting program now.\n\n")
        sys.exit()

    """ Create empty lists to fill later.
    These will contain values to be written to csv with ophaned devices and DNs """


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
    print("\n\nCreating orphan_devs file.\n\n")

    """Establish the length of the orphan list to iterate through. """
    orph_len=len(orph_list)
    for rows in range(0,orph_len):
        orph_matrix.write(orph_list[rows]+',')
        orph_matrix.write(orph_dn_list[rows]+'\n')

    orph_matrix.close()

    if orph_len == 0:
        print("\n\nThere are no orphans. Nothing to clean up. Exiting program.")
        sys.exit()


def destroyOrphDevsDNs(wsdl,cucm,username,password,orph_list,orph_dn_list,del_option,row_types):
    """
     variables:
     orph_list- list of orphaned devices generated by running orphanFinder function.
     orph_dn_list- list of orphaned DNs associated with each device in orph_list, aslo generated by orphanFinder.
     del_option- integer value to indicate whether to delete device or devices and DNs
     row_types- string value representing what is being deleted to be printed back to user.
    """

    axl=AXL(username,password,wsdl,cucm)
    orph_len=len(orph_list)

    print(4*"***WARNING***")
    print("**This action cannot be undone!!\n")
    if del_option == 1:
        print("**Orphaned CSF devices and their DNs will be destroyed!!")
    if del_option == 2:
        print("**Orphaned CSF devices will be destroyed!!")
    print(4*"***WARNING***")
    print('\n')

    q_del=int(input("\n\nHow many "+row_types+" at a time in the bulk delete (can be 1 or more)?: "))

    if q_del > orph_len:
        q_del=orph_len

    if q_del > 0:
        runs=int(orph_len / q_del)
        rmndr=int(orph_len % q_del)
    else:
        print("\n\nInput must be an integer greater than 0. Exiting Program.")
        sys.exit()

    if runs == 0:
        print("\n\nNo orphans to delete. Exiting program.\n\n")
        sys.exit()

    i=1
    j=0

    if del_option == 1:
        while i <= runs:
            for rows in range(j,q_del+j):
                print("Deleting: "+orph_list[rows]+" with DN: "+orph_dn_list[rows]+" . ")
                axl.client.service.removePhone (name=orph_list[rows])
                axl.client.service.removeLine (pattern=orph_dn_list[rows])
                j+=1
            i+=1
            contn=input("Continue with bulk deletion? (Y to continue): ")
            if contn == "Y":
                continue
            else:
                print("\n\nNot continuing bulk deletion based on user input. Exiting program.\n\n")
                sys.exit()
        for rows in range (runs*q_del, runs*q_del+rmndr):
            print("Deleting: "+orph_list[rows]+" with DN: "+orph_dn_list[rows]+" . ")
            axl.client.service.removePhone (name=orph_list[rows])
            axl.client.service.removeLine (pattern=orph_dn_list[rows])

        print("\n\nComplete. No orphans left to delete. Exiting program.\n\n")
        sys.exit()

    if del_option == 2:
        while i <= runs:
            for rows in range(j,q_del+j):
                print("Deleting: "+orph_list[rows]+" . ")
                axl.client.service.removePhone (name=orph_list[rows])
                j+=1
            i+=1
            contn=input("Continue with bulk deletion? (Y to continue): ")
            if contn == "Y":
                continue
            else:
                print("\n\nNot continuing bulk deletion based on user input. Exiting program.\n\n")
                sys.exit()
        for rows in range (runs*q_del, runs*q_del+rmndr):
            print("Deleting: "+orph_list[rows]+" . ")
            axl.client.service.removePhone (name=orph_list[rows])

        print("\n\nComplete. No orphans left to delete. Exiting program.\n\n")
        sys.exit()

    else:
        print("\n\nAn illegal value was entered (must be an 'M'  or 'S'). Exiting program.\n\n")
        sys.exit()



if __name__=="__main__":
    cwd=(os.getcwd())
    print("Looking for AXLAPI.wsdl in current working directory:\n{cwd}\n\n\n".format(cwd=cwd))
    orph_list=[]
    orph_dn_list=[]
    wsdl = 'file:///'+cwd+'/AXLAPI.wsdl'
    cucm=input("Please enter the target CUCM address: ")
    username=input("Please enter AXL username: ")
    password=getpass.getpass("Please enter the AXL password: ")
    orphanFinder(wsdl,cucm,username,password, orph_list, orph_dn_list)
    kill=input("\n\nWould you like to REMOVE orphaned phone devices? (Y or N): ")
    if kill == 'Y':
        kill_DN=input("\n\nWould you also like to REMOVE the associated DNs?(Y or N):")
        if kill_DN == 'Y':
            del_option=1
            row_types="Phones and DNs"
        if kill_DN == 'N':
            del_option=2
            row_types="Phones"
        destroyOrphDevsDNs(wsdl,cucm,username,password,orph_list,orph_dn_list,del_option,row_types)
    elif kill == 'N':
        print("Not removing devices or DNs. Exiting program.")
        sys.exit()
    else:
        print("\n\nAn illegal value was entered (must be an 'Y'  or 'N'). Exiting program.\n\n")
        sys.exit()
