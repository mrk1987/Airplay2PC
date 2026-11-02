# Security

Run Airplay2PC on a trusted home network. It accepts incoming AirPlay traffic
and uses an experimental third-party receiver. Don't forward its ports to
the internet or enable it on a public network.

Windows may ask whether Python can accept incoming connections. Allow it on
your private network if you want to receive audio. Setup doesn't add firewall
rules, install a service or require administrator access.

Pairings, settings and logs stay in `runtime/` on your PC. Logs can include
device names, addresses and protocol metadata. Check them before attaching
them to an issue. Never upload pairing files or credentials.

For a security issue, use GitHub's private vulnerability reporting on this
repository. Include the version, affected code and steps to reproduce with
dummy data. Please keep secrets and private device details out of the report.

The 0.1 release has had focused publication and dependency checks, not a full
security audit of the upstream AirPlay implementation.
