FROM debian:bullseye

RUN apt update
RUN apt upgrade -y
RUN apt install -y curl gpg
RUN curl http://piggledy.org/repo/apt/debian/public.gpg.key | gpg --dearmor > /usr/share/keyrings/piggledy.gpg
RUN echo 'deb [signed-by=/usr/share/keyrings/piggledy.gpg] http://piggledy.org/repo/apt/debian bullseye main' > /etc/apt/sources.list.d/piggledy.list
RUN echo 'deb http://deb.debian.org/debian bullseye-backports main' > /etc/apt/sources.list.d/bullseye-backports.list
RUN apt update
RUN apt install -y -t bullseye-backports python3-django
RUN apt install -y sosse
RUN apt-get clean autoclean
RUN apt-get autoremove --yes
RUN rm -rf /var/lib/cache /var/lib/log /usr/share/doc /usr/share/man

