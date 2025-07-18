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
xpg8logo.append("# https://xpg8.ehlo.email | https://github.com/smck83/expurgate-solo ")
from cmath import log
from sys import stdout
from time import sleep
from time import strftime
import dns.resolver
import re
from datetime import datetime
import os
import signal
from pathlib import Path
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

if 'DISCORD_WEBHOOK' in os.environ and re.match('^https:\/\/discord.com\/api\/webhooks\/.*',os.environ['DISCORD_WEBHOOK'], re.IGNORECASE):
    discordwebhook = os.environ['DISCORD_WEBHOOK']
else:
    discordwebhook = None


if 'UPTIMEKUMA_PUSH_URL' in os.environ and re.match('^http.*\/api\/push\/.*\&ping\=',os.environ['UPTIMEKUMA_PUSH_URL'], re.IGNORECASE):
    uptimekumapushurl = os.environ['UPTIMEKUMA_PUSH_URL']
else:
    uptimekumapushurl = None

if 'SOURCE_PREFIX_OFF' in os.environ:
    source_prefix_off = os.environ['SOURCE_PREFIX_OFF']
else:
    source_prefix_off = False # set to True to be able to run against root domain, for flattening a specific host you don't control e.g. replace include:_spf.google.com which needs 3 lookups with include:%{ir}._spf.google.com._spf.yourdomain.com or include:outbound.mailhop.org which needs 4 lookups with include:%{ir}.outbound.mailhop.org._spf.yourdomain.com

if 'SOURCE_PREFIX' in os.environ:
    source_prefix = os.environ['SOURCE_PREFIX']
else:
    source_prefix = "_xpg8"

if 'NS_RECORD' in os.environ:
    ns_record = os.environ['NS_RECORD']
else:
    ns_record = None

if 'SOA_HOSTMASTER' in os.environ:
    soa_hostmaster = os.environ['SOA_HOSTMASTER']
else:
    soa_hostmaster = None

def restdb(restdb_url,restdb_key):
    payload={}
    headers = {
    'Content-Type': 'application/json',
    'x-apikey': restdb_key
    }

    domains = []
    try:
        response = requests.request("GET", restdb_url, headers=headers, data=payload)
    except:
        print("Error - restdb request failed")
        return mydomains    # added 12.May.23
    else:
        out = response.text
        aList = json.loads(out)
        jsonpath_expression = parse("$..domain")

        for match in jsonpath_expression.find(aList):
            domains.append(match.value)
        if len(domains) > 0:
            return domains
        else:                   # added 12.May.23
            return mydomains    # added 12.May.23


if 'MY_DOMAINS' in os.environ and restdb_url == None:
    domains = os.environ['MY_DOMAINS']
    mydomains = domains.split(' ') # convert input string to list
    mydomains = [domain for domain in mydomains if '.' in domain] # confirm domain contains a fullstop
    mydomains = list(dict.fromkeys(mydomains)) # dedupe the list of domains
elif restdb_url != None:
    restdbdomains = restdb(restdb_url,restdb_key)
    if len(restdbdomains) > 0:
        mydomains = restdbdomains

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

def messageDiscord (content,delay:int=1):
    time.sleep(delay)
    if discordwebhook != None and content != None:
        body = {
            "content" : str(content)
        }
        headers = {
            "Content-Type" : "application/json"

        }
        #print(str(json.dumps(body)))
        try:
            requests.post(discordwebhook,headers=headers,data=str(json.dumps(body)))
            print("SUCCESS: Discord - Message")
        except Exception as e:
            print("ERROR: Discord - Message",e)

def dnsLookup(domain,type,countDepth="on"):
    global depth
    global cacheHit
    mydomains_source_success_status = False
    lookupKey = domain + "-" + type
    if lookupKey not in dnsCache:
        try:
            lookup = [dns_record.to_text() for dns_record in dns.resolver.resolve(domain, type).rrset]

        except Exception as e:
            error = "ERROR : Unhandled exception - " + domain + "[" + type + "]"
            if type != "AAAA": # dont log failed ipv6 address lookups
                print(error)
                header.append("# " + error)
            print(e)
            if depth == 0 and type=="TXT":
                mydomains_source_failure.append(domain)
        else:
            if depth == 0 and type=="TXT":
                for record in lookup:
                    if record != None and re.match('^"v=spf1 ', record, re.IGNORECASE): # check if the first lookup record has a TXT SPF record.
                        mydomains_source_success_status = True

                if mydomains_source_success_status == True: # using boolean, so as to only add 1 record (incase a domain has multiple v=spf1 records)
                    mydomains_source_success.append(domain)
                else:
                    mydomains_source_failure.append(domain) # has TXT record, but no SPF records.
                    print(domain,lookup)
                    time.sleep(1)
            dnsCache[lookupKey] = lookup
            print("++[CACHE][" + domain + "] Added to DNS Cache - " + type)
            if countDepth=="on":
                depth += 1

            return lookup 
    else:
        lookup = dnsCache[lookupKey]
        if depth == 0 and type == "TXT":
            for record in lookup:
                if record != None and re.match('^"v=spf1 ', record, re.IGNORECASE): # check if the first lookup record has a TXT SPF record.
                    mydomains_source_success_status = True

            if mydomains_source_success_status == True: # using boolean, so as to only add 1 record (incase a domain has multiple v=spf1 records)
                mydomains_source_success.append(domain)
            else:
                mydomains_source_failure.append(domain) # has TXT record, but no SPF records.
                print(domain,lookup)
                time.sleep(1)        
        
        if countDepth=="on":
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
        elif depth == 0: #i.e. source_prefix_off == True
            header.append("# Source of truth:  " + domain + " - Will not work in production unless you replace a single record. e.g. include:" + domain + " with include:{ir}." + domain + "._spf.yourdomain.com")
            result = dnsLookup(domain,"TXT")
        else:
           result = dnsLookup(domain,"TXT")
   
    except:
        print("An exception occurred, check there is a DNS TXT record with SPpF present at: " + str(source_prefix) + "." + str(domain) )
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
                            header.append("# " + error)
                            print(error)
                            #print(error,file=sys.stderr)
                    elif re.match('^(\+|)ptr\:', spfPart, re.IGNORECASE):
                            otherValues.append(spfPart)
                            ipmonitor.append(spfPart)
                    elif re.match('^(\+|)ptr', spfPart, re.IGNORECASE):
                            otherValues.append(spfPart + ':' + domain)
                            ipmonitor.append(spfPart + ':' + domain)                         
                    elif re.match('^(\+|)a\:', spfPart, re.IGNORECASE):
                        spfValue = spfPart.split(':')
                        result = dnsLookup(spfValue[1],"A")
                        result6 = dnsLookup(spfValue[1],"AAAA")  
                        if result:
                            header.append("# " + (paddingchar * depth) + " " + spfPart)
                            result = [(x + ' # a:' + spfValue[1]) for x in result]
                            result.sort()
                            for record in result:
                                ip4.append(record)
                        if result6:
                            header.append("# " + (paddingchar * depth) + " " + spfPart)
                            result6 = [(x + ' # aaaa:' + spfValue[1]) for x in result6]
                            result6.sort()
                            for record in result6:
                                ip6.append(record)
                    elif re.match('^(\+|)a', spfPart, re.IGNORECASE):
                        result = dnsLookup(domain,"A")
                        result6 = dnsLookup(domain,"AAAA")
                        if result:  
                            header.append("# " + (paddingchar * depth) + " " + spfPart + "(" + domain + ")")
                            result = [x + " # a(" + domain + ")" for x in result]
                            result.sort()
                            for record in result:
                                ip4.append(record)
                        if result6:  
                            header.append("# " + (paddingchar * depth) + " " + spfPart + "(" + domain + ")")
                            result6 = [x + " # aaaa(" + domain + ")" for x in result6]
                            result6.sort()
                            for record in result6:
                                ip6.append(record)
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
                                result = dnsLookup(hostname,"A","off")  
                                result6 = dnsLookup(hostname,"AAAA","off")
                                if result:
                                    result = [x + ' # ' + spfPart + '=>a:' + hostname for x in result]
                                    result.sort()
                                    for record in result:
                                        ip4.append(record)
                                    header.append("# " + (paddingchar * depth) + " " + spfPart + "=>a:" + hostname)
                                if result6:
                                    result6 = [x + ' # ' + spfPart + '=>aaaa:' + hostname for x in result6]
                                    result6.sort()
                                    for record in result6:
                                        ip6.append(record)
                                    header.append("# " + (paddingchar * depth) + " " + spfPart + "=>aaaa:" + hostname)
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
                                result = dnsLookup(hostname,"A","off")  
                                result6 = dnsLookup(hostname,"AAAA","off")
                                if result:
                                    result = [x + ' # mx(' + domain + ')=>a:' + hostname for x in result ]
                                    result.sort()
                                    for record in result:
                                        ip4.append(record)
                                    header.append("# " + (paddingchar * depth) + " mx(" + domain + ")=>a:" + hostname)
                                if result6:
                                    result6 = [x + ' # mx(' + domain + ')=>aaaa:' + hostname for x in result6 ]
                                    result6.sort()
                                    for record in result6:
                                        ip6.append(record)
                                    header.append("# " + (paddingchar * depth) + " mx(" + domain + ")=>aaaa:" + hostname)
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

def rbldnsrefresh():
    rbldnsdpid = int(-1)
    try:
        rbldnsdpid = Path('/var/run/rbldnsd.pid').read_text().strip()
        rbldnsdpid = int(rbldnsdpid)
    except: 
        print("Couldnt locate /var/run/rbldnsd.pid","Will not be able to tell rbldnsd to refresh config.")
    
    if rbldnsdpid > -1:
        print(f"Notifying rbldnsd there is a change and to refresh the config file(via SIGHUP to pid:{rbldnsdpid})")
        try:
            os.kill(int(rbldnsdpid), signal.SIGHUP)
        except Exception as e:
            print("Uh-oh! Something went wrong, check 'rbldnsd' is running :",e)
        else:
            print(f"Success notifying pid: {rbldnsdpid}")

while totaldomaincount > 0:
    mydomains_source_success = []
    mydomains_source_failure = []
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
    if ns_record != None:
        xpg8logo.append("$NS 3600 " + ns_record + ".")
        if soa_hostmaster != None:
        # Replace the first occurrence of '@' with '.' in soa_hostmaster
            soa_hostmaster_mod = soa_hostmaster.replace('@', '.', 1)
            xpg8logo.append("$SOA 0 " + ns_record + ". " + soa_hostmaster_mod + ". 0 10800 3600 604800 3600")

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
        allIp = []
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
        ip4header.append("$DATASET ip4set:"+ domain +" " + domain)

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
        ip6header.append("$DATASET ip6trie:"+ domain + " " + domain)
        ip6header.append(":3:v=spf1 ip6:$ " + spfActionValue)
        ip6block.append("0:0:0:0:0:0:0:0/0 # all other IPv6 addresses")
        allIp = ip4 + ip6
        header.append("# IP & Subnet: " + str(len(allIp)))
        ipmonitor.sort() # sort for comparison
        print(stdoutprefix + 'Comparing CURRENT and PREVIOUS record for changes.')
        if (domain in ipmonitorCompare) and (ipmonitorCompare[domain] != ipmonitor):
            changeDetected += 1
            print(stdoutprefix + 'Change detected! Total Changes:' + str(changeDetected))
            print(stdoutprefix + 'Previous Record: ' + str(ipmonitorCompare[domain]))
            print(stdoutprefix + 'New Record: ' + str(ipmonitor))
            ipAdded = [d for d in ipmonitor if d not in ipmonitorCompare[domain]]
            ipRemoved = [d for d in ipmonitorCompare[domain] if d not in ipmonitor]
            print(stdoutprefix + 'Change Summary: +' + str(ipAdded) + ' -' + str(ipRemoved) )
            changeResult = (strftime("%Y-%m-%dT%H:%M:%S", time.localtime()) + ' | CHANGE:' + domain + " | " + "+" + str(ipAdded) + " -" + str(ipRemoved) + '\n')
            append2disk(changeResult,'change.log')
            messageDiscord(changeResult)
            ipmonitorCompare[domain] = ipmonitor
            
        elif (domain in ipmonitorCompare) and (ipmonitorCompare[domain] == ipmonitor):
            print(stdoutprefix + 'Exact match! - No change detected')

        else:
            changeDetected += 1
            messageDiscord(stdoutprefix + 'First run, or a domain has only just been added:  \n\n+' + str(ipmonitor),2)
            print(stdoutprefix + 'Change detected - First run, or a domain has only just been added.')

            ipmonitorCompare[domain] = ipmonitor

        # Join all the pieces together, ready for file output
        myrbldnsdconfig = header + ip4header + list(set(ip4)) + ip4block + ip6header + list(set(ip6)) + ip6block # Change ip4 and ip6 to set() to remove duplicate rows 16.06.23 - will not help if IP is duplicate from multiple source hostnames (e.g. different # comment appended)
    
        # Build running config
        runningconfig = runningconfig + myrbldnsdconfig
        print(stdoutprefix + 'Required ' + str(depth) + ' lookups.')
    if changeDetected > 0  and len(mydomains) == len(mydomains_source_success):
        totalChangeCount += 1
        src_path = r'/var/lib/rbldnsd/runningconfig.staging'
        dst_path = r'/var/lib/rbldnsd/running-config'               
        try:
            write2disk(src_path,dst_path,runningconfig)
        except:
            write2disk('runningconfig.staging','running-config',runningconfig)
        lastChangeTime = strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
        time.sleep(1)
        rbldnsrefresh() # tell rbldnsd to rescan <dst_path> for changes
    elif len(mydomains_source_failure) > 0:
        source_failure_output = f"{stdoutprefix} ERROR: {len(mydomains_source_success)} out of {len(mydomains)} of your domains in MY_DOMAINS resolved successfully."
        messageDiscord (str(source_failure_output))
        print(source_failure_output)
        print("ERROR: Ensure each domain in MY_DOMAINS has a valid SPF record setup at SOURCE_PREFIX.<domainname>")
        print("ERROR: No config file written, ensure internet and dns connectivity is working")
        print("ERROR: SPF TXT records requiring attention:",len(mydomains_source_failure),"-", str(mydomains_source_failure))
    else:
        print(f"{len(mydomains_source_success)} out of {len(mydomains)} of your domains in MY_DOMAINS resolved successfully.")
        print("SPF TXT records requiring attention:",len(mydomains_source_failure),"-", str(mydomains_source_failure))
        #print(mydomains_source_success)
        print(f"No issues & no changes detected - No file written (Changes: {str(changeDetected)}, Last change: {lastChangeTime})")
    print("MODE: Running Config")

    end_time = time.time()
    time_lapsed = (end_time - start_time)
    print(strftime("%Y-%m-%dT%H:%M:%S", time.localtime()) + ' | Time Lapsed (seconds):' + str(math.ceil(time_lapsed)))
    if uptimekumapushurl != None:
        time_lapsed = time_lapsed * 1000 # calculate loop runtime and convert from seconds to milliseconds
        print(strftime("%Y-%m-%dT%H:%M:%S", time.localtime()) + " | Pushing Uptime Kuma - endpoint : " + uptimekumapushurl + str(math.ceil(time_lapsed)))
        uptimeKumaPush(uptimekumapushurl + str(math.ceil(time_lapsed)))
    dnsReqTotal = len(dnsCache) + cacheHit
    if dnsReqTotal > 0:
        print(strftime("%Y-%m-%dT%H:%M:%S", time.localtime()) + " | Total Requests:" + str(dnsReqTotal) + " | DNS Cache Size:" + str(len(dnsCache)) + " | DNS Cache Hits:" + str(cacheHit) + " | DNS Cache vs Total:" + str(math.ceil((cacheHit/dnsReqTotal)*100)) + "%")
    else:
        print(strftime("%Y-%m-%dT%H:%M:%S", time.localtime()) + " | Total Requests:" + str(dnsReqTotal) + " | DNS Cache Size:" + str(len(dnsCache)) + " | DNS Cache Hits:" + str(cacheHit))
    print("Total Changes:" + str(totalChangeCount) + " | Last Change:" + lastChangeTime)
    print(strftime("%Y-%m-%dT%H:%M:%S", time.localtime()) + " | Waiting " + str(delayBetweenRun) + " seconds before running again... ")  
    sleep(int(delayBetweenRun)) # wait DELAY in secondsbefore running again.



