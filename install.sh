apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends apt-transport-https ca-certificates curl gnupg2 software-properties-common && \
curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list && \
apt-get update && apt-get install -y --no-install-recommends docker-ce docker-ce-cli containerd.io && \
docker run -p 9001:9001 -p 53:53/udp -e ZONE=_dns.xpg8.tk -e MY_DOMAINS="_netblocks.mimecast.com _spf.google.com email.freshdesk.com spf.protection.outlook.com sendgrid.net mailgun.org outbound.mailhop.org" -e SOURCE_PREFIX_OFF=True --dns 1.1.1.1 --dns 8.8.8.8 --restart always smck83/expurgate-solo


