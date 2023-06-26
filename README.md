# Expurgate Solo
 A self-hosted (single) dockerized SPF solution built on rbldnsd to simplify, hide and exceed limits with SPF records, based on https://github.com/smck83/expurgate

## Environment Variables


| Variable | Description | Required? |
| ------------- | ------------- | ------------- |
| DELAY | This is the delay in seconds between running the script to generate new RBLDNSD config files for RBLDNSD to pickup. `DEFAULT: 300` | N |
| MY_DOMAINS | A list of domains seperated by a space that you want config files to be generated for. Example: `yourdomain.com microsoft.com github.com` | Y |
| SOURCE_PREFIX | This is where you will publish your 'hidden' SPF record; the source of truth e.g. you might host it at _sd3fdsfd.yourdomain.com( so will be SOURCE_PREFIX=_sd3fdsfd) Default: `_xpg8` | N |
| UPTIMEKUMA_PUSH_URL | Monitor expurgate-resolver health (uptime and time per loop) with an [Uptime Kuma](https://github.com/louislam/uptime-kuma) 'push' monitor. URL should end in ping= Example: `https://status.yourdomain.com/api/push/D0A90al0HA?status=up&msg=OK&ping=` | N |
| ZONE | The last part of your SPF record (where rbldnsd is hosted), from step 1(2) EXAMPLE: `_spf.yourdomain.com`  | Y |
| SUPERVISOR_PW | Supervisord is used to run rbldnsd and resolver. Set the password for the web interface DEFAULT: `Expurgate`  - Input as plaintext | N |
| TZ | Timezone e.g. `Australia/Sydney` [more here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)|


Supervisord listening web (HTTP) port: `9001`

Supervisord username: `admin`

Supervisord default password: `Expurgate`

e.g. http://\<host-ip-address\>:9001

Run the container now

`docker run -t -p 9001:9001 -p 53:53/udp -e ZONE=_spf.example.org -e MY_DOMAINS="xpg8.tk" -e SOURCE_PREFIX="_sd6sdyfn" --dns 1.1.1.1 --dns 8.8.8.8 smck83/expurgate-solo`

Run Expurgate Solo on an Amazon Lightsail Debian instance using this in your Launch Script:
NOTE: You will also need to open udp/53 to the host and if you like, tcp/9001 restricted to your IP to access supervisord
````
wget https://raw.githubusercontent.com/smck83/expurgate-solo/main/install.sh && chmod 755 install.sh && ./install.sh
````
