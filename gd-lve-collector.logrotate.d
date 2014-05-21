/var/log/gd-ssl-sync.log {
        size 1M
        notifempty
        copytruncate
        compress
        missingok
        olddir /var/log/gd-ssl-sync
        rotate 10
}

