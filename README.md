# Mijn Simpel Usage Summary Prometheus Exporter

This is a Prometheus Exporter of Usage Summary of Mijn Simplel (simpel.nl) subscriptions.

Update _mijn_simpel_exporter.ini_:
```
[main]
port = 9151
scrape-interval-minutes = 15
username = USERNAME
password = PASSWORD
```

Run:
```
python mijn_simpel_exporter.py mijn_simpel_exporter.ini
```

Check:
```
curl localhost:9151
```

