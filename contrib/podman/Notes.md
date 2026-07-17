Install Moin2 as systemd managed service (podman quadlet)

```bash
cp -p contrib/podman/moin2.container ~/.config/containers/systemd/moin2.container
systemctl --user daemon-reload
systemctl --user start moin2.service
systemctl --user status moin2.service
journalctl --user -xeu moin2.service
```
