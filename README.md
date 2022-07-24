Build images for tl-wdr4300-v1

https://openwrt.org/toh/tp-link/tl-wdr4300_v1

# install image builder

```
wget https://archive.openwrt.org/releases/21.02.1/targets/ath79/generic/openwrt-imagebuilder-21.02.1-ath79-generic.Linux-x86_64.tar.xz
```

# dependency

```
(env) dpavlin@black:~/wifi/lede-ffzg$ sudo apt install zlib1g:amd64
```
# first time install

```
dpavlin@black:~/wifi/lede-ffzg$ virtualenv -p /usr/bin/python3 py3
dpavlin@black:~/wifi/lede-ffzg$ source py3/bin/activate
(py3) dpavlin@black:~/wifi/lede-ffzg$ pip install -r requirements.txt
```

# generate image

```
dpavlin@black:~/wifi/lede-ffzg$ source py3/bin/activate
(py3) dpavlin@black:~/wifi/lede-ffzg$ ./image_gen.py --hostnames wap-test

(py3) dpavlin@black:~/wifi/lede-ffzg$ ls -al images_gen/wap-test/*factory.bin
-rw-r--r-- 1 dpavlin dpavlin 8126464 Apr  9 09:47 images_gen/wap-test/openwrt-21.02.1-ath79-generic-tplink_tl-wdr4300-v1-squashfs-factory.bin
```

# flash existing ap to new version

```
(py3) dpavlin@black:~/wifi/lede-ffzg$ ./image_gen.py --hostnames wap-test --flash
```

## flash manually

```
dpavlin@black:~/wifi/lede-ffzg$ scp images_gen/wap-test/openwrt-21.02.1-ath79-generic-tplink_tl-wdr4300-v1-squashfs-sysupgrade.bin wap-test:/tmp/

dpavlin@black:~/wifi/lede-ffzg$ ssh wap-test

# preserve existing configuration
root@wap-test:~# sysupgrade /tmp/openwrt-21.02.1-ath79-generic-tplink_tl-wdr4300-v1-squashfs-sysupgrade.bin

# flash configuration from image
echo 3 > /proc/sys/vm/drop_caches
mtd -r write /tmp/openwrt-21.02.1-ath79-generic-tplink_tl-wdr4300-v1-squashfs-sysupgrade.bin firmware
```


# setup tftp recovery

## setup 192.168.0.66 as tftp server

root@siobhan:/home/dpavlin# ifconfig eth1:0 192.168.0.66 netmask 255.255.255.0

## disable firewall

root@siobhan:/srv/tftp# iptables -A INPUT -s 192.168.0.0/24 -j ACCEPT

## configure dnsmasq

```
root@siobhan:/home/dpavlin# vi /etc/dnsmasq.conf

interface=eth1

# for later
dhcp-range=192.168.1.50,192.168.1.150,12h

enable-tftp
tftp-root=/var/tftp

root@siobhan:/home/dpavlin# mkdir /var/tftp
root@siobhan:/home/dpavlin# ln -sf ~vsefer/lede-ffzg/images_gen/wap-test/lede-17.01.1-ar71xx-generic-tl-wdr4300-v1-squashfs-factory.bin /var/tftp/wdr4300v1_tp_recovery.bin
```

power on holding reset button for 10 seconds

## setup vlan 20 if needed

```
root@siobhan:/home/dpavlin# ip link add link eth1 name eth1.20 type vlan id 20
```

# add new ap to dns and radius

add client to dot1x

/etc/freeradius/clients.conf

add dns to dns01


# switch ports info

use `swconfig dev switch0 show | less` to see switch ports

0 - cpu
1 - blue internet port
2-5 - other 4 yellow ports numbered 1-4
