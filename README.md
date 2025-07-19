# Expurgate Solo
 A self-hosted (single) dockerized SPF solution built on rbldnsd to simplify, hide and exceed limits with SPF records, based on https://github.com/smck83/expurgate

 For more detail around the functionality of this solution, please refer to: https://github.com/smck83/expurgate/blob/main/README.md

## Environment Variables


| Variable | Description |
| ------------- | ------------- |
| ZONE `REQUIRED` | The last part of your SPF record (where rbldnsd is hosted) EXAMPLE: `_spf.yourhostingdomain.com`|
| MY_DOMAINS `REQUIRED` | A list of domains seperated by a space that you want config files to be generated for. Example: `yourdomain.com microsoft.com github.com`|
| SOURCE_PREFIX `REQUIRED` | This is where you will publish your 'hidden' SPF record; the source of truth e.g. you might host it at _sd3fdsfd.yourdomain.com( so will be SOURCE_PREFIX=_sd3fdsfd) Default: `_xpg8` |
| DELAY | This is the delay in seconds between running the script to generate new RBLDNSD config files for RBLDNSD to pickup. `DEFAULT: 300` |
| UPTIMEKUMA_PUSH_URL | Monitor expurgate-resolver health (uptime and time per loop) with an [Uptime Kuma](https://github.com/louislam/uptime-kuma) 'push' monitor. URL should end in ping= Example: `https://status.yourdomain.com/api/push/D0A90al0HA?status=up&msg=OK&ping=` |
| SUPERVISOR_PW | Supervisord is used to run rbldnsd and resolver. Set the password for the web interface - Input as plaintext or as SHA1. e.g. `{SHA}93eb18474e9067ff5a6f98c54b8854026cee02cb` -  DEFAULT: `Expurgate`|
| TZ | Timezone e.g. `Australia/Sydney` [more here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)|
| DISCORD_WEBHOOK | Discord Channel Webhook for push notifications e.g. `https://discord.com/api/webhooks/123456789101112/ZXhwdXJnYXRlIGlzIGFtYXppbmcgOik` [more here](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks)|
| NS_RECORD | Set the hostname of your nameserver (e.g. spf-ns.yourdomain.com) to comply with DNS compliance standards `DEFAULT: None` |
| SOA_HOSTMASTER | Set the e-mail address to populate an SOA record with your - If you use this, `NS_RECORD` is also required. `DEFAULT: None` |


Supervisord listening web (HTTP) port: `9001`

Supervisord username: `admin`

Supervisord default password: `Expurgate`

e.g. http://\<host-ip-address\>:9001

Run the container now

`docker run -t -p 9001:9001 -p 53:53/udp -e ZONE=_spf.example.org -e MY_DOMAINS="xpg8.tk" -e SOURCE_PREFIX="_sd6sdyfn" --dns 1.1.1.1 --dns 8.8.8.8 smck83/expurgate-solo`

Run Expurgate Solo on an Amazon Lightsail Debian instance using this in your Launch Script:
NOTE: You will also need to open udp/53 to the host and if you like, tcp/9001 restricted to your IP to access supervisord
````
wget https://raw.githubusercontent.com/smck83/expurgate-solo/main/install.sh && chmod 755 install.sh && ./install.sh && \
docker run -d -p 9001:9001 -p 53:53/udp -e ZONE=_dns.xpg8.tk -e MY_DOMAINS="mydomain1.com mydomain2.com mydomain3.com" -e SOURCE_PREFIX="_z6y43d" --dns 1.1.1.1 --dns 8.8.8.8 --restart always smck83/expurgate-solo


````

Check out my tutorial to run Expurgate Solo in an Amazon Lightsail debian instance:

[![How to run Expurgate Solo for SPF Macro hosting in Amazon Lightsail](https://img.youtube.com/vi/MeUNizXkdU8/0.jpg)](https://www.youtube.com/watch?v=MeUNizXkdU8)


# Buy me a coffee
If this was useful, feel free to [Buy me a coffee](https://www.buymeacoffee.com/smc83)
