# author: https://github.com/smck83/
xpg8logo = ["# "]
xpg8logo.append("#  ______                                  _       ")
xpg8logo.append("# |  ____|                                | |      ")
xpg8logo.append("# | |__  __  ___ __  _   _ _ __ __ _  __ _| |_ ___ ")
xpg8logo.append("# |  __| \ \/ / '_ \| | | | '__/ _` |/ _` | __/ _ \\")
xpg8logo.append("# | |____ >  <| |_) | |_| | | | (_| | (_| | ||  __/")
xpg8logo.append("# |______/_/\_\ .__/ \__,_|_|  \__, |\__,_|\__\___|")
xpg8logo.append("#             | |               __/ |              ")
xpg8logo.append("#             |_|              |___/               \n#")
xpg8logo.append("# https://xpg8.tk | https://github.com/smck83/expurgate-solo ")
from cmath import log
from sys import stdout
from time import sleep
from time import strftime
import dns.resolver
import re
from datetime import datetime
import os
import shutil
import time
import math
import requests
import json
import ipaddress
import sys
from jsonpath_ng.ext import parse

paddingchar = "^"
spfActionValue ="~all" # default spfAction if lookup fails or not present
ipmonitorCompare = {}
loopcount = 0
totalChangeCount = 0
lastChangeTime = "No changes"

if 'RESTDB_URL' in os.environ:
    restdb_url = os.environ['RESTDB_URL']
else:
    restdb_url = None

if 'RESTDB_KEY' in os.environ:
    restdb_key = os.environ['RESTDB_KEY']
else:
    restdb_key = None

if 'UPTIMEKUMA_PUSH_URL' in os.environ and re.match('^http.*\/api\/push\/.*\&ping\=',os.environ['UPTIMEKUMA_PUSH_URL'], re.IGNORECASE):
    uptimekumapushurl = os.environ['UPTIMEKUMA_PUSH_URL']
else:
    uptimekumapushurl = None

if 'SOURCE_PREFIX_OFF' in os.environ:
    source_prefix_off = os.environ['SOURCE_PREFIX_OFF']
else:
    source_prefix_off = False # set to True to be able to run against root domain, for vendor flattening e.g. replace include:_spf.google.com which needs 3 lookups with include:%{ir}._spf.google.com._spf.yourdomain.com or include:outbound.mailhop.org which needs 4 lookups with include:%{ir}.outbound.mailhop.org._spf.yourdomain.com

if 'SOURCE_PREFIX' in os.environ:
    source_prefix = os.environ['SOURCE_PREFIX']
else:
    source_prefix = "_xpg8"

def restdb(restdb_url,restdb_key):
    payload={}
    headers = {
    'Content-Type': 'application/json',
    'x-apikey': restdb_key
    }

    domains = []
    response = requests.request("GET", restdb_url, headers=headers, data=payload)
    out = response.text
    aList = json.loads(out)
    jsonpath_expression = parse("$..domain")

    for match in jsonpath_expression.find(aList):
        domains.append(match.value)

    return domains

if 'MY_DOMAINS' in os.environ and restdb_url == None:
    domains = os.environ['MY_DOMAINS']
    mydomains = domains.split(' ') # convert input string to list
    mydomains = [domain for domain in mydomains if '.' in domain] # confirm domain contains a fullstop
    mydomains = list(dict.fromkeys(mydomains)) # dedupe the list of domains
elif restdb_url != None:
    mydomains = restdb(restdb_url,restdb_key) 
else:
    source_prefix_off = True
    mydomains = ['_spf.google.com','_netblocks.mimecast.com','spf.protection.outlook.com','outbound.mailhop.org','spf.messagelabs.com','mailgun.org','sendgrid.net','service-now.com'] # demo mode
    print("MY_DOMAIN not set, running in demo mode using " + str(mydomains))

totaldomaincount = len(mydomains)

if 'DELAY' in os.environ and int(os.environ['DELAY']) > 29:
    delayBetweenRun = os.environ['DELAY']
else:
    delayBetweenRun = 300 #default to 5 minutes
print("Running delay of : " + str(delayBetweenRun))

def append2disk(input,filename):
    with open("/opt/expurgate/" + filename,"a") as file2append:
        file2append.write(str(input))

def write2disk(src_path,dst_path,myrbldnsdconfig):
    with open(src_path, 'w') as fp:
        for item in myrbldnsdconfig:
            # write each item on a new line
            fp.write("%s\n" % item)
    shutil.move(src_path, dst_path)
    print("[" + str(loopcount) + ': CHANGE DETECTED] Writing config file:' + dst_path)

def ipInSubnet(an_address,a_network):
    an_address = ipaddress.ip_address(an_address)
    a_network = ipaddress.ip_network(a_network)
    address_in_network = an_address in a_network
    return address_in_network 

def uptimeKumaPush (url):
    try:
        x = requests.get(url)
    except:
        print("ERROR: Uptime Kuma - push notification",file=sys.stderr)

def dnsLookup(domain,type):
    global depth
    global cacheHit
    lookupKey = domain + "-" + type
    if lookupKey not in dnsCache:
        try:
            lookup = [dns_record.to_text() for dns_record in dns.resolver.resolve(domain, type).rrset]    
        except dns.resolver.NXDOMAIN:
            error = "ERROR : No such domain %s" % domain + "[" + type + "]"
            print(error,file=sys.stderr)
            header.append("# " + error)
        except dns.resolver.Timeout:
            error = "ERROR : Timed out while resolving %s" % domain + "[" + type + "]"
            print(error,file=sys.stderr)
            header.append("# " + error)
        except dns.exception.DNSException:
            error = "ERROR : Unhandled exception - " + domain + "[" + type + "]"
            print(error,file=sys.stderr)
            header.append("# " + error)
        else:
            dnsCache[lookupKey] = lookup
            print("++[CACHE][" + domain + "] Added to DNS Cache - " + type)
            depth += 1 
            return lookup 
    else:
        lookup = dnsCache[lookupKey]
        depth += 1
        cacheHit += 1
        print("==[CACHE][" + domain + "] Grabbed from DNS Cache - " + type)
        return lookup  

def getSPF(domain):
    global depth
    try:
        if depth == 0 and source_prefix_off == False:
            sourcerecord = source_prefix + "." + domain
            header.append("# Source of truth:  " + sourcerecord)
            result = dnsLookup(sourcerecord,"TXT")
        elif depth == 0:
            header.append("# Source of truth:  " + domain + " - Will not work in production unless you replace a single record. e.g. include:" + domain + " with include:{ir}." + domain + "._spf.yourdomain.com")
            result = dnsLookup(domain,"TXT")
        else:
           result = dnsLookup(domain,"TXT")
   
    except:
        print("An exception occurred, check there is a DNS TXT record with SPF present at: " + str(source_prefix) + "." + str(domain) )
    if result:
        for record in result:
            if record != None and re.match('^"v=spf1 ', record, re.IGNORECASE):
                # replace " " with nothing which is used where TXT records exceed 255 characters
                record = record.replace("\" \"","")
                # remove " character from start and end
                spfvalue = record.replace("\"","")
                spfParts = spfvalue.split()
                header.append("# " + (paddingchar * depth) + " " + domain)           
                header.append("# " + (paddingchar * depth) + " " + spfvalue)

                for spfPart in spfParts:
                    if re.match('^[\+\-\~\?](all)$', spfPart, re.IGNORECASE):
                        spfAction.append(spfPart)
                    elif re.match('redirect=', spfPart, re.IGNORECASE):
                        spfValue = spfPart.split('=')       
                        if spfValue[1] != domain and spfValue[1] and spfValue[1] not in includes:
                            includes.append(spfValue[1])
                            getSPF(spfValue[1])
                    elif re.match('^(\+|)include\:', spfPart, re.IGNORECASE) and "%{" not in spfPart:
                        spfValue = spfPart.split(':')
                        if spfValue[1] != domain and spfValue[1] and spfValue[1] not in includes:
                            includes.append(spfValue[1])
                            getSPF(spfValue[1])
                        elif spfValue[1]:
                            error = "WARNING: Loop or Duplicate: " + spfValue[1] + " in " + domain
                            header.append(error)
                            print(error)
                            print(error,file=sys.stderr)
                    elif re.match('^(\+|)ptr\:', spfPart, re.IGNORECASE):
                            otherValues.append(spfPart)
                            ipmonitor.append(spfPart)
                    elif re.match('^(\+|)ptr', spfPart, re.IGNORECASE):
                            otherValues.append(spfPart + ':' + domain)
                            ipmonitor.append(spfPart + ':' + domain)                         
                    elif re.match('^(\+|)a\:', spfPart, re.IGNORECASE):
                        spfValue = spfPart.split(':')
                        result = dnsLookup(spfValue[1],"A")  
                        if result:
                            header.append("# " + (paddingchar * depth) + " " + spfPart)
                            result = [(x + ' # a:' + spfValue[1]) for x in result]
                            result.sort() # sort
                            result = ('\n').join(result)
                            ip4.append(result)
                    elif re.match('^(\+|)a', spfPart, re.IGNORECASE):
                        result = dnsLookup(domain,"A")
                        if result:  
                            header.append("# " + (paddingchar * depth) + " " + spfPart + "(" + domain + ")")
                            result = [x + " # a(" + domain + ")" for x in result]
                            result.sort() # sort
                            result = ('\n').join(result)
                            ip4.append(result)
                    elif re.match('^(\+|)mx\:', spfPart, re.IGNORECASE):
                        spfValue = spfPart.split(':')
                        result = dnsLookup(spfValue[1],"MX") 
                        if result:    
                            header.append("# " + (paddingchar * depth) + " " + spfPart)   
                            mxrecords = []
                            for mxrecord in result:
                                mxValue = mxrecord.split(' ')
                                mxrecords.append(mxValue[1])
                            mxrecords.sort()
                            for hostname in mxrecords:
                                result = dnsLookup(hostname,"A")  
                                if result:
                                    result = [x + ' # ' + spfPart + '=>a:' + hostname for x in result]
                                    result.sort() # sort
                                    result = ('\n').join(result)
                                    ip4.append(result)
                                    header.append("# " + (paddingchar * depth) + " " + spfPart + "=>a:" + hostname)

                    elif re.match('^(\+|)mx', spfPart, re.IGNORECASE):
                        result = dnsLookup(domain,"MX")
                        if result:
                            header.append("# " + (paddingchar * depth) + " mx(" + domain + ")")
                            mxrecords = []
                            for mxrecord in result:
                                mxValue = mxrecord.split(' ')
                                mxrecords.append(mxValue[1])
                            mxrecords.sort()
                            for hostname in mxrecords:
                                result = dnsLookup(hostname,"A")  
                                if result:
                                    result = [x + ' # mx(' + domain + ')=>a:' + hostname for x in result ]
                                    result.sort() # sort
                                    result = ('\n').join(result)
                                    ip4.append(result)
                                    header.append("# " + (paddingchar * depth) + " mx(" + domain + ")=>a:" + hostname)

                    elif re.match('^(\+|)ip4\:', spfPart, re.IGNORECASE):
                        spfValue = re.split("ip4:", spfPart, flags=re.IGNORECASE)
                        if spfValue[1] not in ipmonitor:
                            if re.match('^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/([1-2][0-9]|[3][0-1])$',spfValue[1]): #later check IP against subnet and if present in subnet, ignore.
                                ipmonitor.append(spfValue[1])
                                ip4.append(spfValue[1] + " # subnet:" + domain)
                            elif re.match('^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(\/32)?$',spfValue[1]): #later check IP against subnet and if present in subnet, ignore.
                                ipmonitor.append(spfValue[1])
                                ip4.append(spfValue[1] + " # ip:" + domain)
                            else:
                                ip4.append("# error:" + spfValue[1] + " for " + domain)
                        else:
                            header.append('# ' + (paddingchar * depth) + ' [Skipped] already added (ip4):' + spfValue[1] + " " + domain)
                    elif re.match('(\+|)ip6\:', spfPart, re.IGNORECASE):
                        spfValue = re.split("ip6:", spfPart, flags=re.IGNORECASE)
                        if spfValue[1] not in ipmonitor:
                            ipmonitor.append(spfValue[1])
                            ip6.append(spfValue[1] + " # " + domain)
                        else:
                            header.append('# ' + (paddingchar * depth) + ' [Skipped] already added (ip6):' + spfValue[1] + " " + domain)
                    elif re.match('v\=spf1', spfPart, re.IGNORECASE):
                        spfValue = spfPart
                    elif re.match('exists\:', spfPart, re.IGNORECASE) or re.match('include\:', spfPart, re.IGNORECASE):
                        print('Added to fail response record:',spfPart)
                        ipmonitor.append(spfPart)
                        otherValues.append(spfPart)
                    #else: drop everything else

while totaldomaincount > 0:
    dnsCache = {}
    loopcount += 1
    changeDetected = 0
    cacheHit = 0
    if restdb_url != None:
        try:
            mydomains = restdb(restdb_url,restdb_key) 
        except:
            error = "Error: restdb connection"
            print(error)
            print(error,file=sys.stderr)
        else:
            totaldomaincount = len(mydomains)
    runningconfig = []
    runningconfig = runningconfig + xpg8logo
    runningconfig.append("# Running config for: " + str(totaldomaincount) + ' domains' )
    runningconfig.append("# Source domains: " + ', '.join(mydomains))
    runningconfig.append("#\n#")
    start_time = time.time()
    print('Scanning SPF Records for domains: ' + str(mydomains))
    domaincount = 0
    for domain in mydomains:
        domaincount +=1
        datetimeNow = datetime.now(tz=None)
        headersummary = "# Automatically generated rbldnsd config by Expurgate[xpg8.tk] for:" + domain + " @ " + str(datetimeNow)
        header = []
        header.append(headersummary)
        ip4 = []
        ip4header = []
        ip6 = []
        ip6header = []
        spfAction = []
        otherValues = []
        depth = 0        
        includes = []
        ipmonitor = []
        stdoutprefix = '[' + str(loopcount) + ": " + str(domaincount) + '/' + str(totaldomaincount) + '][' + domain + "] "
        print(stdoutprefix + 'Looking up SPF records.')
        getSPF(domain)
        
    # strip spaces
        ip4 = [x.strip(' ') for x in ip4]
        ip6 = [x.strip(' ') for x in ip6]
    # CREATE ARRAYS FOR EACH PART OF THE RBLDNSD FILE
        header.append("# Depth:" + str(depth))
        # Set SPF Action
        if len(spfAction) > 0:
            spfActionValue = spfAction[0]
        #header.append("# SPF Cache Hits:" + str(cacheHit))
        ip4header.append("$DATASET ip4set:"+ domain +" " + domain + " @")

        ip4header.append(":3:v=spf1 ip4:$ " + spfActionValue)
        if len(otherValues) > 0:
            therValues = list(dict.fromkeys(otherValues)) #dedupe
            ip4block = [":99:v=spf1 " + ' '.join(otherValues) + " " + spfActionValue]
            ip6block = [":99:v=spf1 " + ' '.join(otherValues) + " " + spfActionValue]
        else:
            ip4block = [":99:v=spf1 " + spfActionValue]
            ip6block = [":99:v=spf1 " + spfActionValue]
        ip4block.append("0.0.0.0/1 # all other IPv4 addresses")
        ip4block.append("128.0.0.0/1 # all other IP IPv4 addresses")
        ip6header.append("$DATASET ip6trie:"+ domain + " " + domain + " @")
        ip6header.append(":3:v=spf1 ip6:$ " + spfActionValue)
        ip6block.append("0:0:0:0:0:0:0:0/0 # all other IPv6 addresses")
        header.append("# IP & Subnet: " + str(len(ipmonitor)))
        ipmonitor.sort() # sort for comparison
        print(stdoutprefix + 'Comparing CURRENT and PREVIOUS record for changes.')
        if (domain in ipmonitorCompare) and (ipmonitorCompare[domain] != ipmonitor):
            changeDetected += 1
            lastChangeTime = strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
            print(stdoutprefix + 'Change detected! Total Changes:' + str(changeDetected))
            print(stdoutprefix + 'Previous Record: ' + str(ipmonitorCompare[domain]))
            print(stdoutprefix + 'New Record: ' + str(ipmonitor))
            ipAdded = [d for d in ipmonitor if d not in ipmonitorCompare[domain]]
            ipRemoved = [d for d in ipmonitorCompare[domain] if d not in ipmonitor]
            print(stdoutprefix + 'Change Summary: +' + str(ipAdded) + ' -' + str(ipRemoved) )
            append2disk((strftime("%Y-%m-%dT%H:%M:%S", time.localtime()) + ' | CHANGE:' + domain + " | " + "+" + str(ipAdded) + " -" + str(ipRemoved) + '\n'),'change.log')
            #append2disk(('\n[[[[ CHANGE:' + domain + ' ]]]]\nPrevious Record: ' + str(ipmonitorCompare[domain]) + "\nNew Record:" + str(ipmonitor) + '\n' ),'change.log')
            ipmonitorCompare[domain] = ipmonitor
            
        elif (domain in ipmonitorCompare) and (ipmonitorCompare[domain] == ipmonitor):
            print(stdoutprefix + 'Exact match! - No change detected')

        else:
            changeDetected += 1
            print(stdoutprefix + 'Change detected - First run, or a domain just added.')
            #append2disk(('\nADDED:' + domain + "-" + "+[" + str(ipmonitor) + "] -[]\n"),'change.log')
            #append2disk(('\n[[[[ NEW:' + domain + ' ]]]]\nPrevious Record: []' + "\nNew Record:" + str(ipmonitor) + '\n' ),'change.log')
            ipmonitorCompare[domain] = ipmonitor

        # Join all the pieces together, ready for file output
        myrbldnsdconfig = header + ip4header + ip4 + ip4block + ip6header + ip6 + ip6block
    
        # Build running config
        runningconfig = runningconfig + myrbldnsdconfig
        print(stdoutprefix + 'Required ' + str(depth) + ' lookups.')
    if changeDetected > 0:
        if loopcount > 1: # dont increment totalChangeCount on first run
            totalChangeCount += 1
        src_path = r'/var/lib/rbldnsd/runningconfig.staging'
        dst_path = r'/var/lib/rbldnsd/running-config'               
        write2disk(src_path,dst_path,runningconfig)
    else:
        print("No changes detected - No file written (" + str(changeDetected) + ")")
    print("MODE: Running Config")

    end_time = time.time()
    time_lapsed = (end_time - start_time)
    print(strftime("%Y-%m-%dT%H:%M:%S", time.localtime()) + ' | Time Lapsed (seconds):' + str(math.ceil(time_lapsed)))
    if uptimekumapushurl != None:
        time_lapsed = time_lapsed * 1000 # calculate loop runtime and convert from seconds to milliseconds
        print(strftime("%Y-%m-%dT%H:%M:%S", time.localtime()) + " | Pushing Uptime Kuma - endpoint : " + uptimekumapushurl + str(math.ceil(time_lapsed)))
        uptimeKumaPush(uptimekumapushurl + str(math.ceil(time_lapsed)))
    dnsReqTotal = len(dnsCache) + cacheHit
    print(strftime("%Y-%m-%dT%H:%M:%S", time.localtime()) + " | Total Requests:" + str(dnsReqTotal) + " | DNS Cache Size:" + str(len(dnsCache)) + " | DNS Cache Hits:" + str(cacheHit) + " | DNS Cache vs Total:" + str(math.ceil((cacheHit/dnsReqTotal)*100)) + "%")
    print("Total Changes:" + str(totalChangeCount) + " | Last Change:" + lastChangeTime)
    print(strftime("%Y-%m-%dT%H:%M:%S", time.localtime()) + " | Waiting " + str(delayBetweenRun) + " seconds before running again... ")  
    sleep(int(delayBetweenRun)) # wait DELAY in secondsbefore running again.



