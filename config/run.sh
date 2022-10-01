cp /opt/expurgate/config/rbldnsd.conf /etc/supervisor/conf.d/
cp /opt/expurgate/config/resolver.conf /etc/supervisor/conf.d/
cp /opt/expurgate/config/supervisord.conf /etc/supervisor/supervisord.conf

if [ -z "${ZONE}" ]
then
echo command=/usr/sbin/rbldnsd -b 0.0.0.0 -n -e -t 5m -f -l - _default.xpg8.tk:combined:/var/lib/rbldnsd/running-config >> /etc/supervisor/conf.d/rbldnsd.conf
else
echo command=/usr/sbin/rbldnsd -b 0.0.0.0 -n -e -t 5m -f -l - $ZONE:combined:/var/lib/rbldnsd/running-config >> /etc/supervisor/conf.d/rbldnsd.conf
fi

if [ -z "${SUPERVISOR_PW}" ]
then
echo password=expurgate >> /etc/supervisor/supervisord.conf
else
echo password=$SUPERVISOR_PW >> /etc/supervisor/supervisord.conf
fi