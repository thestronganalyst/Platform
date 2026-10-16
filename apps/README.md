# apps/

Private records of generated apps, one folder per app: the manifest it was generated from (`platform.yaml`) and the resolved lock (`platform.lock.yaml`: modules, versions, config, build order, target path, layout).

Flat apps (the default, docs/adr/0004-flat-apps.md) carry none of this themselves, so this folder is how the platform knows what each app contains and which module updates apply to it.
