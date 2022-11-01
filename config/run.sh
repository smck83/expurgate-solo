#!/bin/bash
cp /opt/expurgate/config/rbldnsd.conf /etc/supervisor/conf.d/
cp /opt/expurgate/config/resolver.conf /etc/supervisor/conf.d/
cp /opt/expurgate/config/supervisord.conf /etc/supervisor/supervisord.conf

if [ -z "${ZONE}" ]
then
echo command=/usr/sbin/rbldnsd -b 0.0.0.0 -n -e -t 5m -f -l - _default.xpg8.tk:combined:/var/lib/rbldnsd/running-config >> /etc/supervisor/conf.d/rbldnsd.conf
else
echo command=/usr/sbin/rbldnsd -b 0.0.0.0 -n -e -t 5m -f -l - $ZONE:combined:/var/lib/rbldnsd/running-config >> /etc/supervisor/conf.d/rbldnsd.conf
fi

if [ -z "${SUPERVISOR_PW}" ];then
echo Not set && echo password={SHA}93eb18474e9067ff5a6f98c54b8854026cee02cb >> /etc/supervisor/supervisord.conf
elif [[ $SUPERVISOR_PW == "{SHA}"* ]];then
echo Received as SHA && echo password=$SUPERVISOR_PW >> /etc/supervisor/supervisord.conf
else
echo Not received as SHA && echo password=\{SHA\}$(echo -n "$SUPERVISOR_PW" | sha1sum | awk '{print $1}') >> /etc/supervisor/supervisord.conf
fi

/usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf